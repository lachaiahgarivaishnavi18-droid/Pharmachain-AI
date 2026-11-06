# RL methodology and reproducibility

## Inventory MDP

A 90-day, single-product pharmaceutical simulation tracks age-bucket batches, stochastic daily demand, lead-time pipeline, capacity and FEFO consumption. PPO uses a continuous fraction in [0,1] mapped to 0–500 units. DQN uses 11 actions in 50-unit increments. Both cap accepted orders at free inventory-position capacity; proposed excess incurs a constraint penalty. Expired batches are removed before consumption. Orders arrive after four simulated days with 35-day shelf life. Initial stock is 200 units, capacity 1,000 units. Demand is Normal(25 + 6 sin(2π day/7), 6), truncated/rounded at zero.

Observation has 16 float features: on-hand stock, position, recent mean demand, naive forecast, standard deviation, lead time, pipeline, safety stock, reorder point, near-expiry units, capacity, holding/stockout/waste cost indicators, criticality and cold-storage indicator. Features are normalized and clipped. Several cost/criticality features are constants in this toy environment. Product inference maps recent observed demand, usable inventory and approved pipeline into this state, but the policy was trained on one stylized distribution. Product-specific deployment requires retraining, distribution checks, expiry-state mapping and safety validation. No claim of robust transfer across products is made.

Reward = 2×served − 12×unmet − .03×closing stock − 15×order indicator − .1×ordered units − 4×expired units − 20×proposed excess units − .01×stock cold exposure proxy. Reward weights are configurable constructor values and unit-tested. Evaluation cost excludes fulfillment reward but includes penalties; these are simulated cost units, not rupees.

Actions occur before future demand sampling; only past demand enters the observation. Training seed is 42. Evaluation demand seeds are 100–104, identical across fixed reorder point, min-max, EOQ, forecast and RL policies. All use FEFO. Metrics cover total cost, service level, days with stockout, average stock, wastage, frequency, fulfillment and constraint requests. Counts describe proposed capacity violations even when the environment caps accepted orders.

## Cold-chain environment

The separate 96-step simulation has 15-minute decision intervals and configurable lower/upper temperature limits. Actions are monitoring, investigation, escalation, recommended alternative storage, recommended rerouting and equipment inspection. It contains no medicine use, release or discard action. Temperature effects of recommendations are stylized simulated response assumptions, not measured equipment behavior. The evaluation compares threshold alerting, trailing anomaly screening and agentic rule response; an optional PPO checkpoint adds an RL comparison. Results depend strongly on those assumed response effects.

## Commands (project root, Python 3.12)

```powershell
.\.venv\Scripts\python.exe -m rl.training.train_inventory_policy --algorithm PPO --timesteps 4096 --seed 42 --path rl/models/experiment-ppo
.\.venv\Scripts\python.exe -m rl.training.train_inventory_policy --algorithm DQN --timesteps 10000 --seed 42 --path rl/models/experiment-dqn
.\.venv\Scripts\python.exe -m rl.evaluation.compare_baselines --path rl/models/experiment-ppo.zip --algorithm PPO
.\.venv\Scripts\python.exe -m rl.training.train_cold_chain_policy --timesteps 4096
.\.venv\Scripts\python.exe -m rl.evaluation.compare_cold_chain --path rl/models/cold-chain.zip
```

Use the UI's training action to train and register a policy automatically for application inference. CPU is the tested default; GPU configuration is a future extension. Longer training, multiple training seeds, confidence intervals, ablations, realistic censored-demand modeling, variable lead times and independent real-world validation are needed for academic effectiveness claims. A short smoke experiment establishes executable infrastructure only.
