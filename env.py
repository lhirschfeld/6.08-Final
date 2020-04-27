import serial
import gym
import time
import numpy as np

PORT_NAME             = '/dev/ttyACM1'
MOUNT_OFFSET          = 152
RAIL_TRAVEL           = 5120
ENCODER_TICKS_PER_REV = 4096
TORQUE_SCALING        = 50
HARDWARE_FREQUENCY    = 1000/20

class HillGym(gym.Env):
    def _only_hardware(f):
        def guarded(self, *args, **kwargs):
            if not self.real:
                raise Exception(f'Cannot run method "{f.__name__}" in simulation.')
            
            return f(self, *args, **kwargs)
        
        return guarded

class HillCartpole(HillGym):
        
    def __init__(self, verbose=False):
        self.verbose = verbose
        
        try:
            self.ser  = serial.Serial(PORT_NAME)
            self.real = True
        except serial.SerialException as e:
            if self.verbose:
                print(e)
            
            self.real = False
            
            # TODO: set up simulation variables
        
        self.timesteps = 0
            
    def reset(self):
        if self.real:
            self.enable_quadrature_homing()
            self.home()
            self.get_observation() #  blocks until homing is complete
            self.disable_quadrature_homing()
        
        else:
            pass
        
        self.timesteps = 0
        return self.get_observation()
    
    @HillGym._only_hardware
    def enable_quadrature_homing(self):
        self.ser.write("cq\r".encode())
    
    @HillGym._only_hardware
    def disable_quadrature_homing(self):
        self.ser.write("cd\r".encode())
    
    @HillGym._only_hardware
    def home(self):
        self.ser.write("ch\r".encode())
    
    @HillGym._only_hardware
    def torque(self, t):
        self.ser.write((str(t)+'\r').encode())
    
    @HillGym._only_hardware
    def read_state(self):
        self.ser.flushInput()
        raw = self.ser.readline().decode().strip().split(' ')

        if len(raw) != 4:
            return self.read_state()

        try:
            return [float(s) for s in raw]
        except:
            return self.read_state()
    
    def step(self, action):
        action = np.clip(action, self.action_space.low, self.action_space.high)
        if self.real:
            self.torque(TORQUE_SCALING*action[0])
        else:
            # TODO: perform forward dynamics
            pass
        
        obs = self.get_observation()
        reward = self.get_reward(obs, action)
        done = self.is_done(obs)
        
        self.timesteps += 1
        
        return obs, reward, done, {}
    
    def is_done(self,obs):
        pass
    
    def get_reward(self, obs, action):
        pass
    
    def get_observation(self):
        if self.real:
            q_cart, qd_cart, q_pole, qd_pole = self.read_state()
            
            return np.array([
                2 * q_cart  / RAIL_TRAVEL,
                2 * qd_cart / RAIL_TRAVEL,
                2*np.pi*(q_pole - MOUNT_OFFSET)/(ENCODER_TICKS_PER_REV),
                2*np.pi*qd_pole/ENCODER_TICKS_PER_REV
            ])
        
        # TODO: read simulation variables for simulator
    
    @property
    def action_space(self):
        return gym.spaces.Box(low=-1, high=1, shape=(1,))

    @property
    def observation_space(self):
        return gym.spaces.Box(
            low= [-1,-np.inf,-np.inf,-np.inf],
            high=[1,  np.inf, np.inf, np.inf],
        shape=(4,))


if __name__ == "__main__":
    env = HillCartpole()
    env.reset()