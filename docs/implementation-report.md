# Implementation and verification report

## Completed in this workspace

- React/Vite/TypeScript frontend with login and eleven operational pages, Tailwind styling, Axios, Recharts, Lucide and React Flow.
- FastAPI backend, SQLAlchemy persistence, SQLite local startup, PostgreSQL Compose configuration, initial Alembic migration and OpenAPI documentation.
- Five-role authentication, scrypt password hashes, expiring JWTs, server-side authorization, user creation and persistent audits.
- Product/supplier/warehouse creation and management APIs; batch stock receipts, FEFO stock-out/transfers, reservations/adjustments, availability accounting, expiry and quarantine controls.
- Chronological demand forecast evaluation using moving average, exponential smoothing, random forest, optional ARIMA and XGBoost. Product-level history, metrics and forecast chart.
- Inventory and cold-chain Gymnasium environments, PPO/DQN inventory training implementation, PPO cold-chain training, saved policies and seeded baseline evaluation scripts.
- Backend training jobs, versioned registered checkpoints, inference without retraining and a candidate-performance gate that retains the forecast baseline for weak candidates.
- Product-specific temperature checks, validated synthetic readings, monotonic timestamp enforcement, sensor failure/gap alerts, excursion duration/extrema, affected batch IDs, quarantine and authorized investigation.
- Supplier catalog constraints, safety stock/ROP/EOQ, draft order pricing, explicit manager/admin approval or rejection with reason and actor. No supplier communication.
- All ten specialized LangGraph nodes with shared structured state, Pydantic output validation, actual timings, error records and partial results. User-triggered and optional single-process scheduled analysis.
- Local explanation provider, optional HTTPS gateway interface and deterministic fallback. External text cannot mutate decisions.
- CSV/JSON datasets, product/demand import UI, inventory PDF report, Dockerfiles, Compose, PowerShell startup helper and architecture/research/deployment documentation.

## Partially completed / intentionally bounded

- RL: real smoke training and held-out evaluation run; inventory PPO is **not converged** and materially underperforms baselines. It fails the screening gate and is not used for recommendations. This is an infrastructure/research baseline, not demonstrated optimization improvement.
- Cold-chain risk: trailing statistical anomaly/trend screening exists; there is no calibrated predictive excursion classifier or product stability model.
- Explanations: provider abstraction and generic gateway contract exist; no vendor-specific paid LLM has been connected or evaluated.
- Forecasts: product-level daily horizon implemented. Warehouse/regional aggregation, holiday/promotion features, LSTM and calibrated intervals are not implemented.
- Reports: inventory PDF summary and record-level CSV/JSON exports implemented. A comprehensive formatted management PDF combining every model/agent report is not implemented.
- Settings: core configuration and user creation have UI controls; advanced product updates, sensor setup, warehouse/catalog mapping and batch adjustments are API-driven. Retention is stored as a preference with no automatic deletion.
- Data: all required seed counts exist. Simulated historical ledger rows are labeled independent examples, not reconstructed opening-balance history.
- Jobs/scheduling: in-process background training and interval analysis work for one process. No durable queue, cancellation, distributed scheduler or retries/backoff system exists.
- Pagination/filtering covers major data endpoints; it is not consistent across every small list. UI types use a generic record type for several API responses rather than generated OpenAPI clients.

## Not implemented

Real IoT authentication/adapters, carrier/rerouting APIs, live supplier delivery history, automated email/SMS notifications, multiwarehouse RL allocation, constrained network optimization with OR-Tools/PuLP, pharmaceutical disposition procedures, validated stability databases, SSO/MFA/refresh sessions, tenant isolation, production login throttling, fully automated browser E2E tests, external hosting and pharmaceutical regulatory validation.

No quarantine release, autonomous medicine use/discard, or automated supplier-spending operation is provided.

## Actual verification (2026-11-06)

| Check | Observed result |
|---|---|
| Backend/API/RL tests | **22 passed** (including Gym checks, FEFO, reservations, transfer/capacity, approvals, excursions/recovery, sensor gaps/failure, forecasts, ten-agent execution, imports/exports, policy gate and model checkpoint round trip) |
| Frontend tests | **23 passed** across component/routing and connected-page interactions |
| TypeScript | `tsc -b` completed successfully |
| Vite production build | Completed successfully; vendor/chart/workflow chunks separated |
| SQLite migration | `alembic ... upgrade head` completed successfully |
| Inventory PPO | 4,096 CPU steps, seed 42; registered `ppo-1`; five held-out evaluation seeds |
| Cold-chain PPO | 4,096 CPU steps, seed 42; separate saved checkpoint; ten-seed response comparison executed |
| Synthetic dataset export | Initial counts: 50 products, 5 warehouses, 10 suppliers, 150 batches, 600 ledger rows, 18,250 demand days, 10 shipments, 480 readings |
| Live integrated API workflow | Completed: new product/batch/demand, forecast, policy screening, excursion/recovery retaining 60 quarantined units, quality investigation, draft/approval, 10 completed agents, PDF generated |
| Visual browser verification | In-app browser timed out loading localhost twice; no claim of visual/browser E2E completion |
| Docker/PostgreSQL | Configuration supplied; container startup and PostgreSQL behavior not executed in this environment |

Initial tests exposed a test-lifespan database fixture error, which was corrected. Frontend page tests initially exposed null-handling mistakes in the test mocks, which were corrected before the passing run. Vite required broader filesystem access than the restricted sandbox; the build passed with that access. No tests are claimed for unexecuted external deployments, real sensor hardware, external LLM gateways or DQN convergence.

The machine-readable records are `docs/evaluation-results.json`, `docs/cold-chain-evaluation.json` and `docs/live-verification.json`. Ignored local artifacts include `pharmachain.db`, `rl/models/ppo-1.zip`, `rl/models/cold-chain.zip`, frontend build output and `data/exports/integrated-report.pdf`. The live verification adds one explicitly synthetic product/batch and corresponding demand/alert/order records, so current counts exceed the initial seed counts.

## Startup and research commands

### Vercel deployment follow-up

The app was subsequently deployed to production at https://pharmachain-ai-chi.vercel.app in the ResumeProject team. The hosted backend uses a dedicated free Neon PostgreSQL database in Singapore, a generated sensitive JWT signing key, an atomic PostgreSQL bootstrap, and portable NumPy inference exported from the actual PPO checkpoint. Cloud training and the in-process scheduler are explicitly disabled; local training remains available. The deployment retains Vercel authentication protection. Source and deployment metadata are in `deployment/`, `scripts/prepare-vercel.py`, `docs/vercel-deployment-result.json`, and `docs/vercel-deployment.md`. Executed remote check results are recorded in `docs/vercel-verification.json` after completion. Docker runtime remains unverified.

From project root: `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`.

From `frontend`: `pnpm dev`. Login `admin` / `<your-configured-demo-password>` in the initial local demonstration.

Training/evaluation: see README.md and rl_methodology.md for PPO, DQN, cold-chain and baseline commands. Runtime dependencies are in backend/requirements.txt; the executed environment is pinned in backend/requirements-lock.txt and frontend/pnpm-lock.yaml. Python 3.12, CPU PyTorch and Node 22+ are the intended runtimes. Model checkpoints are local runtime artifacts rather than committed source.
