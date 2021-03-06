import serial, sys, glob, gym, time, os
import serial.tools.list_ports
import numpy as np

MOUNT_OFFSET          = 152
RAIL_TRAVEL           = 5120
ENCODER_TICKS_PER_REV = 4096
TORQUE_SCALING        = 50
VELOCITY_SCALING      = 700

HARDWARE_FREQUENCY    = 1000/20
SIMULATION_FREQUENCY  = 1000/10
MAX_TIMESTEPS         = 400

CART_MASS             = 0.5 # kg
POLE_MASS             = 0.05 # kg
POLE_LENGTH           = 0.2 # m
GRAVITY               = -9.81 # m/s^2

gym.logger.set_level(40)

class HillGym(gym.Env):
    def _only_hardware(f):
        def guarded(self, *args, **kwargs):
            if not self.real:
                raise Exception(f'Cannot run method "{f.__name__}" in simulation.')
            
            return f(self, *args, **kwargs)
        
        return guarded
    
    def _only_simulation(f):
        def guarded(self, *args, **kwargs):
            if self.real:
                raise Exception(f'Cannot run method "{f.__name__}" on hardware.')
            
            return f(self, *args, **kwargs)
        
        return guarded

class HillCartpole(HillGym):
        
    def __init__(
        self,
        cart_mass = CART_MASS,
        pole_mass = POLE_MASS,
        pole_length = POLE_LENGTH,
        timestep_limit = MAX_TIMESTEPS,
        windup_penalty = 0.1,
        trig_observations=False,
        simulation=False,
        verbose=False
    ):
        self.viewer = None
        self.verbose = verbose
        self.timestep_limit = timestep_limit
        self.trig_observations = trig_observations
        self.windup_penalty = windup_penalty # penalty on sqrt of total angular distance
        
        try:
            if simulation:
                raise StopIteration
            
            ports = serial.tools.list_ports.grep('arduino')
            port = next(ports)
            
            self.ser  = serial.Serial(os.path.join('/dev',port.name), timeout=0)
            self.real = True
        except (serial.SerialException, StopIteration) as e:            
            if self.verbose:
                if isinstance(e, serial.SerialException):
                    print("Can't find physical robot due to error:")
                    print(e)
                
                print("Running in simulation mode.")
            
            self.real     = False
            self.q_sim    = np.zeros(4)
            self.dt_sim   = 1/SIMULATION_FREQUENCY
            self.u_repeat = int(SIMULATION_FREQUENCY/HARDWARE_FREQUENCY)
            
            self.cart_mass = cart_mass
            self.pole_mass = pole_mass
            self.pole_length = pole_length
                
        self.timesteps = 0
    
    def make_visualizer(self, width=640, height=480):
        from gym.envs.classic_control import rendering

        self.visualizer_width = width
        self.visualizer_height = height

        self.visualizer_cart_width = 40
        self.visualizer_cart_height = 40
        
        self.visualizer_pole_width = 10
        self.visualizer_pole_height = 100
        
        self.visualizer_border = 50

        self.viewer = rendering.Viewer(
            self.visualizer_width, self.visualizer_height
        )
        
        self.track = rendering.Line(
            (self.visualizer_border, self.visualizer_height/2),
            (self.visualizer_width - self.visualizer_border, self.visualizer_height/2)
        )
        
        self.track.set_color(1,0,0)
        self.viewer.add_geom(self.track)
        
        l,r,t,b = -self.visualizer_cart_width/2, self.visualizer_cart_width/2, self.visualizer_cart_height/2, -self.visualizer_cart_height/2
        cart = rendering.FilledPolygon([(l,b), (l,t), (r,t), (r,b)])
        self.cart_trans = rendering.Transform()
        cart.add_attr(self.cart_trans)
        cart.set_color(0,0,0)
        self.viewer.add_geom(cart)
        
        l,r,t,b = -self.visualizer_pole_width/2, self.visualizer_pole_width/2, self.visualizer_pole_height-self.visualizer_pole_width/2, -self.visualizer_pole_width/2
        pole = rendering.FilledPolygon([(l,b), (l,t), (r,t), (r,b)])
        pole.set_color(0.5, 0.5, 0.5)
        self.pole_trans = rendering.Transform(translation=(0, 0))
        pole.add_attr(self.pole_trans)
        pole.add_attr(self.cart_trans)
        self.viewer.add_geom(pole)

    def render(self, mode='human', close=False, state=None):
        if close:
            if self.viewer is not None:
                self.viewer.close()
                self.viewer = None
            return
        
        if self.viewer is None:
            self.make_visualizer()
        
        if state is None:
            q = self.get_observation()
        else:
            q = state
        
        x, _, theta, _ = q
        
        
        cart_x = x * (self.visualizer_width/2 - self.visualizer_border) + self.visualizer_width/2

        self.cart_trans.set_translation(cart_x, self.visualizer_height/2)
        self.pole_trans.set_rotation(theta + np.pi)
        
        return self.viewer.render(return_rgb_array = mode=='rgb_array')        
        
    def reset(self):
        if self.real:
            self.enable_quadrature_homing()
            self.home()
            self.ser.reset_input_buffer()
            self.get_observation() #  blocks until homing is complete
            self.disable_quadrature_homing()
            self.torque_mode()
        
        else:
            self.q_sim = np.zeros(4)
        
        self.timesteps = 0
        return self.get_observation()
    
    def __del__(self):
        if self.real:
            self.torque_mode()
            self.command(0)
        
        if self.viewer is not None:
            self.render(close=True)

    
    @HillGym._only_simulation
    def step_forward_dynamics(self, u):
        x, xdot, theta, thetadot = self.q_sim
        
        theta = -1 * theta
        
        x_dotdot = (
            u + self.pole_mass * np.sin(theta) * (
                self.pole_length * thetadot**2 + GRAVITY * np.cos(theta)
            )
        ) / (self.cart_mass + self.pole_mass * np.sin(theta)**2)
        
        theta_dotdot = (
            -u*np.cos(theta) -
            self.pole_mass * self.pole_length * thetadot**2 * np.cos(theta) * np.sin(theta) - 
            (self.cart_mass + self.pole_mass) * GRAVITY * np.sin(theta)
        ) / (self.pole_length * (self.cart_mass + self.pole_mass * np.sin(theta)**2))
                
            
        # Euler integration
        qdotdot = np.array([x_dotdot, theta_dotdot])
        qdot_new = self.q_sim[1::2] + qdotdot * self.dt_sim
        q_new = self.q_sim[::2] + self.dt_sim * qdot_new

        self.q_sim = np.stack((q_new, qdot_new)).T.flatten()
            
    @HillGym._only_hardware
    def enable_quadrature_homing(self):
        self.ser.write("cq\r".encode())
    
    @HillGym._only_hardware
    def disable_quadrature_homing(self):
        self.ser.write("cd\r".encode())
    
    @HillGym._only_hardware
    def torque_mode(self):
        self.mode = 't'
        self.ser.write("ct\r".encode())
        self.command(0)
    
    @HillGym._only_hardware
    def velocity_mode(self):
        self.mode = 'v'
        self.ser.write("cv\r".encode())
        self.command(0)
    
    @HillGym._only_hardware
    def home(self):
        self.ser.write("ch\r".encode())
    
    @HillGym._only_hardware
    def command(self, t):
        self.ser.write((str(t)+'\r').encode())
    
    @HillGym._only_hardware
    def read_state(self):
        old_r = None
        r = self.ser.readline().decode().strip().split(' ')
        while len(r) != 4:
            r = self.ser.readline().decode().strip().split(' ')
        
        while len(r) == 4:
            old_r = r
            r = self.ser.readline().decode().strip().split(' ')
        
        try:
            q_cart, qd_cart, q_pole, qd_pole = [float(s) for s in old_r]

            return np.array([
                2 * q_cart  / RAIL_TRAVEL,
                2 * qd_cart / RAIL_TRAVEL,
                2*np.pi*(q_pole - MOUNT_OFFSET)/(ENCODER_TICKS_PER_REV),
                2*np.pi*qd_pole/ENCODER_TICKS_PER_REV
            ])
        
        except:
            return self.read_state()
    
    def step(self, action):
        action = np.clip(action, self.action_space.low, self.action_space.high)[0]
        if self.real:
            scaling = TORQUE_SCALING if self.mode == 't' else VELOCITY_SCALING
            self.command(scaling*action)
        else:
            for _ in range(self.u_repeat):
                self.step_forward_dynamics(action)
        
        obs, q = self.get_observation(include_raw=True)
        reward = self.get_reward(q, action)
        done = self.is_done(obs)
        
        self.timesteps += 1
        
        return obs, reward, done, {}
    
    def is_done(self, obs):
        # Kill trial when too passmuch time has passed
        if self.timesteps >= self.timestep_limit:
            return True
        
        # Kill trial if position limits are near being reached
        if np.abs(obs[0]) > 0.9:
            return True
        
        return False
    
    def get_reward(self, state, action):
        cos_theta = np.cos(state[2])
        
        
        # Give reward from 0 to 1 for pole position.
        # Could also penalize x position, but will not for now.
        reward = 0.5 * (1-cos_theta)
        
        # penalty on sqrt of total angular distance, meant to dissuade
        # helicopter policies.
        reward -= self.windup_penalty * np.sqrt(np.abs(state[2]))
                
        return reward
    
    def get_observation(self, include_raw=False):
        if self.real:
            q_raw = self.read_state()
                    
        else:
            q_raw = np.copy(self.q_sim)
        
        if self.trig_observations:
            q_proc = np.array([
                q_raw[0], q_raw[1], np.cos(q_raw[2]), np.sin(q_raw[2]), q_raw[3]
            ])
        else:
            q_proc = q_raw
        
        if include_raw:
            return q_proc, q_raw
        
        return q_proc
    
    @property
    def action_space(self):
        return gym.spaces.Box(low=-1, high=1, shape=(1,))

    @property
    def observation_space(self):
        if self.trig_observations:
            return gym.spaces.Box(
                low= np.array([-1, -np.inf,-1, -1, -np.inf]),
                high=np.array([1,   np.inf, 1,  1,  np.inf])
            )
            
        return gym.spaces.Box(
            low= np.array([-1., -np.inf, -np.inf, -np.inf]),
            high=np.array([1.,   np.inf,  np.inf,  np.inf])
        )


if __name__ == "__main__":
    env = HillCartpole()
    env.reset()