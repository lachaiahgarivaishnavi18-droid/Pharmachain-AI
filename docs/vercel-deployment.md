# Vercel deployment profile

The production project is `resume-project3/pharmachain-ai`. A dedicated free Neon PostgreSQL resource, `pharmachain-db`, is connected to production/preview environments. Database credentials are injected by the Marketplace integration; JWT_SECRET is a generated sensitive Vercel environment variable. Neither credentials nor Vercel auth files are included in deployment source.

`scripts/prepare-vercel.py` packages reviewed Python source, the built React assets, a freshly generated synthetic snapshot and a portable NumPy export of the actual locally trained PPO policy. Twenty deterministic action comparisons verify the portable export against the PyTorch checkpoint. The deployed inference runtime does not require PyTorch. The original poor-policy screening gate remains enforced; importing a trained model never implies qualification.

`deployment/vercel-entrypoint.py` exposes FastAPI through a Vercel Python function. It normalizes the Neon PostgreSQL URL for psycopg and performs first-time schema/data initialization inside a PostgreSQL transaction protected by an advisory lock. It imports actual local experiment metrics with provenance. Inventory, approvals, readings and agent outputs are persisted in Neon and are never stored in ephemeral SQLite.

PPO/DQN training is disabled in the hosted profile and returns an explicit 503 explanation. Training remains available in local/Docker deployments. Saved-policy inference, baseline comparison, forecasting, the ten-agent workflow and operational modules remain available on Vercel. XGBoost is omitted from the lightweight hosted requirements; optional advanced forecast comparison records its unavailability and still evaluates ARIMA and the three default models. No background interval scheduler runs in the serverless function.

The project retains Vercel's existing default deployment protection. Hosting is a synthetic research demonstration and uses the documented demo credentials; it is not an operational pharmaceutical deployment.

Rebuild/repackage from project root after frontend checks:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare-vercel
cd deploy/vercel
vercel project inspect --non-interactive --scope resume-project3
vercel deploy --prod --yes --scope resume-project3
```

Deployment IDs, URLs, validation outcomes and any runtime limitations are recorded after publication in the deployment result file. `.vercel`, `.env*`, checkpoints and local databases are excluded from upload.
