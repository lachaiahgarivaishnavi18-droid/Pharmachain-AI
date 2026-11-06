import gymnasium as gym
from gymnasium import spaces
import numpy as np

class ColdChainEnv(gym.Env):
    """Operational recommendations only. There is no release, use or discard action."""
    actions = ['additional monitoring', 'investigate', 'escalate', 'recommend alternative storage', 'recommend rerouting', 'inspect equipment']
    def __init__(self, lower=2., upper=8., horizon=96):
        self.lower, self.upper, self.horizon = lower, upper, horizon
        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Box(-100, 200, (9,), dtype=np.float32)
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.day, self.temperature, self.duration, self.trend = 0, (self.lower+self.upper)/2, 0, 0
        return self.observation(), {}
    def observation(self):
        return np.array([self.temperature, self.lower, self.upper, self.trend, self.duration, 1, 1, max(0, self.horizon-self.day), 1], dtype=np.float32)
    def step(self, action):
        if not self.action_space.contains(action): raise ValueError('Invalid action')
        previous = self.temperature
        self.temperature += self.np_random.normal(.12, .5)-(max(0, self.temperature-(self.lower+self.upper)/2)*.35 if action in [3, 4, 5] else 0)
        self.trend = self.temperature-previous
        outside = not self.lower <= self.temperature <= self.upper
        self.duration = self.duration+15 if outside else 0
        self.day += 1
        cost = [1, 3, 5, 12, 15, 8][action]
        return self.observation(), float(-cost-(20 if outside else 0)-(40 if outside and action == 0 else 0)), self.day >= self.horizon, False, {'recommendation': self.actions[action], 'human_review_required': True, 'outside': outside, 'response_cost': cost}
