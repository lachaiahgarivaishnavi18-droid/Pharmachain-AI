# Executed research evaluation

The initial registered inventory PPO policy was trained on CPU for **4,096 steps**, training seed **42**, using Stable-Baselines3. Its saved version is `ppo-1`, checkpoint `rl/models/ppo-1.zip` (ignored runtime artifact). Five held-out evaluation seeds are **100–104**. Every policy uses the same seeded demand sequence and FEFO allocation.

| Policy | Mean simulated cost | Demand service level | Stockout day rate |
|---|---:|---:|---:|
| Fixed reorder point | 850.416 | 99.965% | 0.444% |
| Min-max | 852.896 | 100.000% | 0.000% |
| EOQ | 808.112 | 99.982% | 0.222% |
| Forecast-based | 2172.484 | 100.000% | 0.000% |
| PPO, 4,096 steps | 24446.360 | 8.952% | 91.778% |

The short PPO run **did not learn a competitive replenishment policy**. It placed no replenishment orders under deterministic evaluation. The result demonstrates successful training/checkpoint/evaluation plumbing but does not establish convergence, improvement, research novelty or effectiveness. Results are preserved honestly in `evaluation-results.json` rather than replaced with favorable synthetic numbers.

Application policy screening requires simulated service level >=95% and cost <=120% of the best measured baseline. This PPO candidate fails. The application consequently labels its recommendations **Forecast-based baseline (trained candidate failed screening)**. A passing result would still require operational validation; it is not a product-safety determination or regulatory approval.

The baseline forecast orders frequently and consequently incurs more ordering cost. This is itself a useful experiment: inventory coverage alone is not an adequate optimization objective. EOQ performs best on this toy scenario. Longer training, action/reward tuning, multiple training seeds, confidence intervals and diverse independent scenarios are needed before comparing the proposed approach academically.

A separate cold-chain PPO smoke training runs for 4,096 steps; its artifact is `rl/models/cold-chain.zip`. Cold-chain response comparisons use ten held-out seeds (100–109). See `cold-chain-evaluation.json` for executed metrics. These simulations assume that alternative storage, rerouting or inspection changes temperature dynamics. Such assumptions are deliberately simplified and must not be interpreted as real-world efficacy or medicine stability evidence.

Model environments never authorize product release, disposal or use. Quality disposition remains outside the application.
