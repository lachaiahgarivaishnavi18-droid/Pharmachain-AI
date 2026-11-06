# Pharmachain-AI

**PharmaChain AI**

Reinforcement learning augmented pharmaceutical inventory and cold-chain decision support. Built with React/TypeScript/Vite, FastAPI/SQLAlchemy, LangGraph, Gymnasium and Stable-Baselines3. Runs locally without paid model keys.

Deployed research demo: [PharmaChain AI on Vercel](https://pharmachain-ai-chi.vercel.app). Vercel account sign-in may be required by the project's retained deployment protection. The hosted profile uses persistent Neon PostgreSQL and supports saved-policy inference/evaluation; PPO/DQN training remains local. See [Vercel deployment details](docs/vercel-deployment.md).

**Research demonstration using entirely synthetic data. This is not a validated pharmaceutical operational system or a claim of regulatory compliance.**

## Start on Windows PowerShell

Use Python **3.12**, Node **22+**, and pnpm. Run from the project root.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
corepack enable
pnpm install
pnpm dev
```

Open [the application](http://127.0.0.1:5173) and [interactive API documentation](http://127.0.0.1:8000/docs).

Before first startup, set `$env:DEMO_PASSWORD` to a unique password of at least 12 characters. Credentials are never stored in this repository.

Demo users: `admin`, `manager`, `operator`, `quality`, `viewer`. Their initial password is supplied through `DEMO_PASSWORD` before the first seed. There is no built-in default password. Seeding preserves existing data and does not reset passwords on subsequent launches.

This workspace already has a Python 3.12 virtual environment and frontend dependencies installed. To restart here, run the uvicorn command above, then `pnpm dev` in `frontend`. If pnpm is not on PATH, the bundled command is:

```powershell
node "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\pnpm\bin\pnpm.cjs" dev
```

Python 3.15 is not the verified ML runtime. If `py -3.12` is unavailable in this Codex environment, create the environment using:

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m venv .venv
```

## What works

- Authentication, five roles, scrypt password hashing, JWT sessions and audit trail.
- Product catalog, warehouse storage, batch receipts, FEFO stock-out and transfers, reservations and controlled adjustments through the API.
- Available inventory correctly excludes reserved, expired and quarantined stock.
- Demand forecasting: moving average, exponential smoothing, random forest; optional ARIMA and XGBoost. Chronological selection/test evaluation and approximate uncertainty bands.
- PPO/DQN training jobs, checkpoint persistence, simulated baseline comparison, candidate performance screening and explicit forecast fallback.
- Separate cold-chain Gymnasium environment and response evaluation scripts.
- Product-specific sensor limits, timestamp/health validation, excursion duration/extrema, affected-batch quarantine and quality investigation.
- Supplier catalogs, reorder point/safety stock/EOQ, priced purchase drafts and explicit manager/admin approval.
- Ten tool-based LangGraph agents, validated outputs, actual execution timing, partial-result handling and optional interval scheduling.
- React dashboard, inventory/batch detail, forecast charts, RL workspace, cold-chain monitor, suppliers, orders, React Flow agent monitor, risk register, reports and settings.
- CSV/JSON dataset export, inventory PDF summaries, product/demand JSON or CSV import, user creation.
- SQLite local persistence, Alembic initialization, Docker/PostgreSQL configuration.

No workflow sends supplier orders, releases quarantined products or determines medicine stability. Recovery of temperature does not remove a quality hold.

## Run the research and checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m rl.training.train_inventory_policy --algorithm PPO --timesteps 4096 --seed 42 --path rl/models/experiment-ppo
.\.venv\Scripts\python.exe -m rl.evaluation.compare_baselines --path rl/models/experiment-ppo.zip --algorithm PPO
.\.venv\Scripts\python.exe -m rl.training.train_cold_chain_policy --timesteps 4096
.\.venv\Scripts\python.exe -m rl.evaluation.compare_cold_chain --path rl/models/cold-chain.zip
.\.venv\Scripts\python.exe -m scripts.export-demo
```

With the backend running, `.\.venv\Scripts\python.exe -m scripts.verify-live` exercises product registration, stock receipt, demand import, forecasting, saved-policy screening, excursion/quarantine/recovery, quality investigation, purchase approval, all ten agents and PDF reporting. It adds clearly named synthetic validation records to the demo database.

```powershell
cd frontend
pnpm test
pnpm build
```

CLI checkpoints are not automatically registered with the application. Use the RL workspace **Train policy** button or `POST /api/rl/train` for registered model inference. The actual short PPO experiment underperformed the baselines; a service/cost screening gate therefore keeps the forecast baseline active. See [research evaluation](docs/research_evaluation.md) and machine-readable result files for measured outcomes.

## PostgreSQL / Docker

```powershell
Copy-Item .env.example .env
# Edit .env: set a strong JWT_SECRET, POSTGRES_PASSWORD and DEMO_PASSWORD.
docker compose up --build
```

The frontend is bound to localhost:5173 and API to localhost:8000. PostgreSQL and checkpoints use named volumes. Python local startup reads environment variables supplied by your shell; it does not automatically load `.env`. Docker Compose does. For a local variable, for example: `$env:JWT_SECRET='your-generated-secret'`.

Explicit migrations: `.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head`. SQLite local mode can initialize automatically; Docker uses the migration before startup. Do not use `alembic downgrade` on valuable data: the initial migration drops the research schema.

## Documentation and limits

- [Architecture and safety boundaries](docs/architecture.md)
- [Agent workflow](docs/agent_workflow.md)
- [RL methodology and commands](docs/rl_methodology.md)
- [Dataset documentation](data/README.md)
- [API guide](docs/api.md)
- [Database schema](docs/database_schema.md)
- [Deployment guide](docs/deployment.md)
- [Implementation and verification report](docs/implementation-report.md)

Real IoT/carrier integrations, operational validation, multiwarehouse RL allocation, calibrated stability/risk models, durable job infrastructure, SSO/MFA, automatic data retention, live notifications, comprehensive browser E2E automation and a real external LLM adapter are not complete. The optional explanation gateway is a provider boundary, not an installed vendor integration. See the implementation report for full status.
