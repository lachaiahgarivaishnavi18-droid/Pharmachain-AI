import argparse, json
from pathlib import Path
from stable_baselines3 import PPO, DQN
from stable_baselines3.common.callbacks import BaseCallback
from rl.environments.pharmaceutical_inventory_env import PharmaceuticalInventoryEnv

class History(BaseCallback):
    def __init__(self):
        super().__init__(); self.points = []
    def _on_step(self):
        if self.num_timesteps % 128 == 0:
            self.points.append({'step': self.num_timesteps, 'mean_step_reward': float(self.locals['rewards'].mean())})
        return True

def train(algorithm='PPO', timesteps=4096, seed=42, path='rl/models/policy'):
    env = PharmaceuticalInventoryEnv(discrete=algorithm == 'DQN')
    cls = PPO if algorithm == 'PPO' else DQN
    options = {'n_steps': 256, 'batch_size': 64} if algorithm == 'PPO' else {'learning_starts': 256, 'buffer_size': 10000, 'batch_size': 64}
    model = cls('MlpPolicy', env, seed=seed, device='cpu', verbose=0, policy_kwargs={'net_arch': [64, 64]}, **options)
    history = History()
    model.learn(total_timesteps=timesteps, callback=history)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    model.save(path)
    result = {'algorithm': algorithm, 'seed': seed, 'timesteps': model.num_timesteps, 'path': str(Path(path).with_suffix('.zip')), 'history': history.points, 'simulated': True}
    Path(path+'.json').write_text(json.dumps(result, indent=2))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--algorithm', choices=['PPO', 'DQN'], default='PPO'); parser.add_argument('--timesteps', type=int, default=4096); parser.add_argument('--seed', type=int, default=42); parser.add_argument('--path', default='rl/models/policy')
    args = parser.parse_args(); print(json.dumps(train(**vars(args)), indent=2))
