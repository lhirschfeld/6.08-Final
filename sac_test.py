from env import HillCartpole
from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines.sac.policies import MlpPolicy as SacMlpPolicy
from stable_baselines import SAC

e = HillCartpole(
    verbose=True,
    trig_observations=True,
    windup_penalty=0.1
)

e = DummyVecEnv([lambda: e])

# Each trial of 400 timesteps takes ~14 seconds. Thus, to run for 12 hours
# we would want ~3000 trials.

TRIALS = 3000

model = SAC(SacMlpPolicy, e, verbose=0, seed=0, tensorboard_log="./cartpole_tboard/")

try:
    model.learn(
        total_timesteps=400*TRIALS, tb_log_name='sac'
    )
except KeyboardInterrupt:
    print('Exiting early.')

e.reset()

print('Model learned, saving:')
model.save('sac_learned_windup_01')
