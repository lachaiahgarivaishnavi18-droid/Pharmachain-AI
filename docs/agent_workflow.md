# Structured agent workflow

1. Inventory monitoring aggregates batch availability and shortage indicators.
2. Demand forecasting runs chronological validation and reports held-out metrics.
3. RL optimization loads the latest registered policy, otherwise explicitly identifies the forecast baseline.
4. Cold-chain monitoring queries sensor health and excursion/batch evidence.
5. Cold-chain risk prediction computes trailing z-score and linear trend indicators. Scores are uncalibrated anomaly screening, never product stability.
6. Expiry/batch management lists shelf life in FEFO order, preserving availability statuses.
7. Supplier planning compares catalog costs/reliability and calculates safety stock, reorder point and EOQ.
8. Integrated risk assessment records shortage, excess, shelf-life and quality-hold factors linked to product/batch sources.
9. Decision support consolidates replenishment and quality investigation proposals with evidence, uncertainty and human-review requirements.
10. Orchestrator validates and consolidates the run and partial warnings.

The graph is sequential, keyed by run UUID. Node-level savepoints allow partial completion, but retries are manual by rerunning analysis. Each node writes actual duration, input source summary, structured result and error status. The final API transaction commits all recorded results atomically. An optional in-process interval scheduler uses the same graph; the default is user-triggered execution.
