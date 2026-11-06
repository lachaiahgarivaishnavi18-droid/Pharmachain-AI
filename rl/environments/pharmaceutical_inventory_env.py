import gymnasium as gym
from gymnasium import spaces
import numpy as np

DEFAULT_REWARD = {'fulfillment': 2., 'stockout': 12., 'holding': .03, 'ordering': 15., 'unit_order': .1, 'expiry': 4., 'constraint': 20., 'cold_risk': .01}

def reward_components(served, unmet, stock, ordered, expired, violations, weights=None):
    w = {**DEFAULT_REWARD, **(weights or {})}
    return {'fulfillment': served*w['fulfillment'], 'stockout': -unmet*w['stockout'], 'holding': -stock*w['holding'],
            'ordering': -(w['ordering'] if ordered else 0)-ordered*w['unit_order'], 'expiry': -expired*w['expiry'],
            'constraint': -violations*w['constraint'], 'cold_risk': -stock*w['cold_risk']}

class PharmaceuticalInventoryEnv(gym.Env):
    metadata = {'render_modes': []}
    def __init__(self, discrete=False, horizon=90, capacity=1000, lead_days=4, shelf_life=35, weights=None):
        self.discrete, self.horizon, self.capacity = discrete, horizon, capacity
        self.lead_days, self.shelf_life, self.weights = lead_days, shelf_life, weights
        self.action_space = spaces.Discrete(11) if discrete else spaces.Box(0., 1., (1,), dtype=np.float32)
        self.observation_space = spaces.Box(0., 10., (16,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.day, self.pipeline = 0, []
        self.batches = [[200, self.shelf_life]]
        self.recent = [25.]*14
        return self.observation(), {}

    def observation(self):
        stock = sum(q for q, _ in self.batches)
        pending = sum(q for _, q in self.pipeline)
        mean, std = np.mean(self.recent), np.std(self.recent)
        expiry = sum(q for q, age in self.batches if age <= 7)
        return np.clip(np.array([stock/self.capacity, (stock+pending)/self.capacity, mean/100, mean/100, std/100,
                                self.lead_days/30, pending/self.capacity, 50/self.capacity, (mean*self.lead_days+50)/self.capacity,
                                expiry/self.capacity, self.capacity/1000, .03, .12, .04, 1., 1.], dtype=np.float32), 0, 10)

    def action_quantity(self, action):
        if self.discrete:
            return int(np.asarray(action).item())*50
        return int(float(np.clip(np.asarray(action).reshape(-1)[0], 0, 1))*500)

    def step(self, action):
        if self.discrete and not self.action_space.contains(int(np.asarray(action).item())):
            raise ValueError('Invalid discrete action')
        if not self.discrete and (np.asarray(action).shape != (1,) or not self.action_space.contains(np.asarray(action, dtype=np.float32))):
            raise ValueError('Invalid continuous action')
        ordered = self.action_quantity(action)
        position = sum(q for q, _ in self.batches)+sum(q for _, q in self.pipeline)
        violations = max(0, position+ordered-self.capacity)
        ordered = min(ordered, max(0, self.capacity-position))
        if ordered: self.pipeline.append((self.day+self.lead_days, ordered))
        arrivals = [q for due, q in self.pipeline if due <= self.day]
        self.pipeline = [(due, q) for due, q in self.pipeline if due > self.day]
        self.batches.extend([[q, self.shelf_life] for q in arrivals])
        expired = sum(q for q, age in self.batches if age <= 0)
        self.batches = [[q, age] for q, age in self.batches if age > 0]
        # Only current/past demand enters observation. Future stochastic demand is sampled after the action.
        demand = max(0, int(self.np_random.normal(25+6*np.sin(self.day*2*np.pi/7), 6)))
        unmet = demand
        for batch in sorted(self.batches, key=lambda b: b[1]):
            used = min(batch[0], unmet); batch[0] -= used; unmet -= used
        self.batches = [[q, age-1] for q, age in self.batches if q > 0]
        stock = sum(q for q, _ in self.batches)
        parts = reward_components(demand-unmet, unmet, stock, ordered, expired, violations, self.weights)
        self.recent = (self.recent+[demand])[-14:]
        self.day += 1
        return self.observation(), float(sum(parts.values())), self.day >= self.horizon, False, {'demand': demand, 'served': demand-unmet, 'unmet': unmet, 'stock': stock, 'ordered': ordered, 'expired': expired, 'violations': violations, 'reward_components': parts, 'cost': -sum(v for k, v in parts.items() if k != 'fulfillment')}
