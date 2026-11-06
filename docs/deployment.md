# Deployment guide

The reference deployment is Docker Compose with PostgreSQL 16, FastAPI on Python 3.12 and an nginx-hosted Vite build. The supplied configuration binds exposed services to loopback. It has not been deployed to an external host during implementation.

The frontend pins pnpm 11.25.0 and permits the esbuild dependency build through `allowBuilds`, following [pnpm's documented build policy](https://pnpm.io/cli/approve-builds).

1. Copy `.env.example` to `.env`; supply independently generated strong signing and database secrets. URL-encode special characters in database URL passwords if configuring DATABASE_URL directly.
2. Decide whether this is a synthetic demo. Keep `SEED_DEMO=true` only for demonstration. With `SEED_DEMO=false`, provision the first administrator through a controlled database/bootstrap process; there is deliberately no anonymous registration endpoint.
3. Run `docker compose up --build`. Database health gates backend startup. Alembic creates the schema; frontend nginx proxies `/api` to the backend.
4. Verify `/api/health`, sign-in and read-only dashboards. Run the test suite against disposable infrastructure before any operational use.
5. Back up PostgreSQL and the model volume. Use one backend process while in-process training/scheduling is enabled.

Local SQLite is the default. For PostgreSQL outside Docker, install the included psycopg dependency and set `$env:DATABASE_URL='postgresql+psycopg://user:password@host/database'` before migration and launch. Set `$env:AUTO_CREATE_SCHEMA='false'` once migrations manage the schema.

Operational hosting requires TLS termination, hardened secret management, login rate limits, CSRF/CSP review, operational access control review, audit retention policy, backup/restore testing, resource limits, job cancellation/durable worker queues, application monitoring, device authentication and concurrency/load testing. Public demo credentials must be removed. This document is not a claim that those controls or pharmaceutical validation have been completed.

Remote LLM explanations are optional and disabled. Set LLM_PROVIDER, LLM_EXPLANATION_URL and LLM_API_KEY only for an authorized HTTPS explanation gateway. No browser configuration exposes the API key. Scheduling is optional via ANALYSIS_INTERVAL_SECONDS (>=60) and ANALYSIS_PRODUCT_ID and is not durable across process downtime.
