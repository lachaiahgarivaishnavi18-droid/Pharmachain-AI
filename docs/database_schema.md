# Database schema

`backend/app/models.py` is the ORM schema; `backend/alembic/versions/0001_initial.py` initializes it. The initial migration deliberately reuses current metadata for this first research release. Future schema revisions should use frozen explicit Alembic operations; do not edit this initial migration after an operational deployment.

| Aggregate | Tables / links |
|---|---|
| Identity | users → roles; audit_logs capture actor/action/entity/details |
| Catalog | products, product_categories, warehouses |
| Stock | batches → product and warehouse; inventory_transactions → batch |
| Procurement | suppliers; supplier_products → supplier/product; purchase_orders → supplier; purchase_order_items → order/product; human_approvals → order |
| Demand | demand_history → product; demand_forecasts and forecast_evaluations → product |
| Cold chain | temperature_sensors → product and warehouse or shipment; temperature_readings → sensor; temperature_excursions → sensor with affected batch IDs; cold_chain_alerts → sensor/excursion |
| Logistics | shipments; shipment_items → shipment/batch |
| RL | rl_training_runs; rl_models → training run; rl_policy_evaluations; rl_recommendations → product |
| Intelligence | risk_assessments; agent_executions grouped by run UUID |
| Settings | system_configuration keyed JSON preferences |

Entities have integer primary keys and UTC creation timestamps. Important checks enforce nonnegative batch stock/reservations, valid expiry/manufacturing ordering, product temperature/stock ranges and nonnegative demand. Product/day and sensor/timestamp are unique. Batch identity is unique per batch number/product/warehouse. Historical traceability prevents deleting referenced catalog entities. JSON stores structured model evidence and reports; normalized inventory balance is derived on request, avoiding a second mutable inventory table. Shipment and alert links use foreign keys; affected-batch snapshots intentionally preserve a JSON identifier list. Additional production constraints and referentially normalized exposure links remain future hardening work.
