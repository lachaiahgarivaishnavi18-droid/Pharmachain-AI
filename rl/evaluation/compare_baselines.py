import argparse, json, math
import numpy as np
from rl.agents.policy import load_policy
from rl.environments.pharmaceutical_inventory_env import PharmaceuticalInventoryEnv

def evaluate(path=None, algorithm='PPO', seeds=range(100, 105)):
    model = load_policy(path, algorithm) if path else None
    results = []
    for name in ['Fixed reorder point', 'Min-max', 'EOQ', 'Forecast-based']+(['RL policy'] if model else []):
        episodes = []
        for seed in seeds:
            env = PharmaceuticalInventoryEnv(discrete=algorithm == 'DQN')
            obs, _ = env.reset(seed=seed); done = False; logs = []
            while not done:
                position = sum(q for q, _ in env.batches)+sum(q for _, q in env.pipeline)
                mean = float(np.mean(env.recent))
                if name == 'RL policy': action, _ = model.predict(obs, deterministic=True)
                else:
                    qty = {'Fixed reorder point': 200 if position < 150 else 0,
                           'Min-max': max(0, 350-position) if position < 150 else 0,
                           'EOQ': math.sqrt(2*25*365*15/(.04*365)) if position < 150 else 0,
                           'Forecast-based': max(0, mean*10+50-position)}[name]
                    action = min(10, round(qty/50)) if env.discrete else np.array([min(1, qty/500)], dtype=np.float32)
                obs, _, done, _, info = env.step(action); logs.append(info)
            total_demand = sum(x['demand'] for x in logs)
            episodes.append({'total_cost': sum(x['cost'] for x in logs), 'service_level': sum(x['served'] for x in logs)/max(1,total_demand),
                             'stockout_rate': sum(x['unmet'] > 0 for x in logs)/len(logs), 'average_inventory': np.mean([x['stock'] for x in logs]),
                             'expiry_wastage': sum(x['expired'] for x in logs), 'replenishment_frequency': sum(x['ordered'] > 0 for x in logs),
                             'constraint_violations': sum(x['violations'] > 0 for x in logs), 'demand_fulfillment': sum(x['served'] for x in logs)})
        results.append({'policy': name, **{k: float(np.mean([e[k] for e in episodes])) for k in episodes[0]}})
    return {'simulated': True, 'evaluation_seeds': list(seeds), 'results': results, 'limitations': 'Identical held-out demand seeds; toy single-product model, not evidence of clinical or operational benefit. FEFO is used by every policy.'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--path'); p.add_argument('--algorithm', default='PPO'); p.add_argument('--output', default='docs/evaluation-results.json'); args = p.parse_args()
    result = evaluate(args.path, args.algorithm)
    from pathlib import Path
    Path(args.output).write_text(json.dumps(result, indent=2)); print(json.dumps(result, indent=2))
