# PharmaChain AI architecture

React 19 / Vite / TypeScript / Tailwind renders twelve application experiences (including login). Axios calls FastAPI. Recharts renders measured datasets, and React Flow displays ten LangGraph nodes. The API enforces identity and roles independently of the UI. PostgreSQL is the Docker database; SQLite is the local default.

## Data and safety boundaries

SQLAlchemy models persist products, categories, warehouses, batches, signed stock transactions, suppliers/catalogs, purchase orders/items, demand history/forecasts/evaluations, sensors/readings/excursions/alerts, shipments/items, training runs/models/evaluations/recommendations, risks, agent logs, approvals, audits and configuration. Inventory is a derived batch aggregation rather than a duplicated balance table. Available quantity excludes expired, quarantined and reserved stock. Batches expiring today are unavailable. Stock-out and transfers use FEFO. Every write occurs inside a database transaction. PostgreSQL locks batches and capacity-changing warehouse rows; guarded updates prevent negative stock. SQLite uses serialized writes and returns a retryable 503 on lock contention. Load/concurrency validation remains required before deployment.

Sensors are explicitly associated with one warehouse/product configuration or one shipment. Excursions use that product's temperature limits. Failed sensor values are recorded but not treated as validated product-temperature evidence. Failed/missing readings raise coverage alerts. Out-of-order and duplicate timestamps are rejected. Excursions retain start/end times, observed duration/extrema and affected batch identifiers. Recovery closes exposure but never removes quarantine. Quality users can record investigations. No release, discard or product-safety endpoint exists.

Purchase order drafts use supplier catalog prices and MOQ. Manager/admin approval requires a reason and records the authenticated actor. Approval has no network side effect: supplier communication is not implemented.

## Identity

Passwords use salted scrypt; JWTs expire after eight hours and carry only user ID. Role is read from the database for each request. Viewer: read; operator: stock, product, forecast and analysis writes; manager: supplier/financial approvals/training; quality: investigation; admin: all roles and user creation. JWT signing secrets come from environment; absent secrets produce a process-local random key, invalidating sessions after restart. Demo seeding requires an environment-supplied password of at least 12 characters and must be disabled for operational deployment. Session tokens are held in sessionStorage, not source-controlled secrets. Login throttling, MFA, refresh tokens and SSO are not implemented.

## Forecasts and policies

Forecasting is independent of RL inference. Three models run by default; ARIMA and XGBoost are optional in the comparison. Train/validation/test boundaries are 60/20/20 in time order. Selection uses validation MAE; the selected model alone is evaluated on test and then fitted on all historical observations for the requested future horizon. Recursive tree forecasting never ingests future demand. Approximate residual bands are clearly labeled and are not calibrated coverage intervals.

RL uses Gymnasium and Stable-Baselines3. Versioned checkpoints live outside tracked source. Training jobs run in-process, one at a time; restart marks queued/running jobs interrupted. This is not a durable production queue. CLI training writes files but does not register a model; use the authenticated training endpoint or UI for registered inference. See rl_methodology.md.

## Agent workflow

Each LangGraph node calls a deterministic tool, validates AgentOutput with Pydantic, records actual wall-clock time and writes output/error evidence. Failed nodes roll back their savepoint and pass partial state to downstream nodes. No fabricated logs are seeded. See agent_workflow.md.

Local explanations are deterministic and require no API key. `LLM_PROVIDER=remote`, `LLM_EXPLANATION_URL=https://...` and optional `LLM_API_KEY` enable an external explanation gateway. It receives `{task, evidence, constraints}` and must return `{summary, limitations}`. The gateway can wrap an LLM provider of choice. Network/schema failures fall back locally. Remote text is advisory and is never parsed into stock, purchase, quarantine or policy actions. Evidence sent to a gateway may contain operational records; keep local mode unless authorized.

## Scheduling

`ANALYSIS_INTERVAL_SECONDS=3600` and `ANALYSIS_PRODUCT_ID=1` enable sequential scheduled LangGraph analysis while a single backend process is running. Minimum interval is 60 seconds; default is disabled. User-triggered analysis is always available. For multiple workers use an external scheduler/queue with leader election; do not enable this in every worker.

## Scope limitations

Real sensor adapters, carrier APIs, live supplier history, validated pharmaceutical stability data, operational model calibration, tenant isolation, regulatory validation, automatic retention deletion, email notification delivery, advanced multiechelon optimization and production worker infrastructure are not provided. Stored retention settings are preferences only. Sensor health is evaluated at query/ingest time; no background missing-sensor alert service runs. Warehouse forecasts and capacity-aware multiwarehouse RL allocation remain extensions; current forecasts are product-level and transfers are explicit FEFO operations.
