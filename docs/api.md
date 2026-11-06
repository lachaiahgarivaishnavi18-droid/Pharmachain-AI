# API guide

The running server exposes complete typed OpenAPI at `/openapi.json` and interactive Swagger at `/docs`.

1. `POST /api/auth/login` with `{username,password}` returns an eight-hour access token.
2. Send `Authorization: Bearer TOKEN` on subsequent calls.
3. Product lists accept `q`, `offset` and `limit`; stock lists accept status; batch lists accept product/warehouse; readings accept sensor/limit; executions accept run UUID. Several smaller lists are bounded internally rather than offering full pagination.

Endpoint groups:

| Domain | Main operations |
|---|---|
| Products | GET/POST `/api/products`; GET/PUT/DELETE `/api/products/{id}` |
| Warehouses | GET/POST `/api/warehouses` |
| Inventory | GET `/api/inventory`, `/batches`, `/transactions`, `/low-stock`, `/near-expiry`, `/{product_id}`; POST `/stock-in`, `/stock-out`, `/transfer`, `/batches/{id}/adjust` |
| Forecasts | POST `/api/forecast/run`; GET `/api/forecast`, `/metrics`, `/{product_id}` |
| RL | POST `/api/rl/train`, `/evaluate`, `/recommend`; GET `/models`, `/training-history`, `/policy-performance` |
| Cold chain | POST/GET `/api/cold-chain/readings`; GET `/sensors`, `/warehouses`, `/shipments`, `/alerts`, `/excursions`; POST `/sensors`, `/alerts/{id}/investigate` |
| Suppliers | GET/POST `/api/suppliers`; GET/PUT `/{id}`; POST `/{id}/catalog` |
| Purchase orders | GET/POST `/api/purchase-orders`; GET `/{id}`; POST `/{id}/approve`, `/{id}/reject` |
| Agents | GET `/api/agents`, `/executions`, `/executions/{id}`; POST `/run` with `{product_id}` |
| Analytics | GET `/api/analytics/dashboard`, `/inventory`, `/cold-chain`, `/rl`; GET `/api/risks` |
| Administration | GET/PUT `/api/settings`; GET/POST `/api/users`; GET `/api/audit` |
| Import/export | POST `/api/import/products`, `/demand`; GET `/api/export/{kind}?format=csv|json|pdf` |
| Health | GET `/api/health`, `/api/health/database`, `/api/health/models` |

All financial decisions and investigations require `{reason: "at least five characters"}`. Only manager/admin can approve purchase orders; quality/admin can investigate. Operator stock-out example:

```json
{"product_id": 1, "warehouse_id": 1, "quantity": 10, "reference": "Synthetic demonstration allocation"}
```

Insufficient usable stock, duplicate records and state conflicts return 409. Invalid schemas return 422 with Pydantic field details. Missing entities return 404; unauthorized/forbidden calls return 401/403. SQLite lock contention returns 503. Error bodies use a `detail` field. Unexpected exceptions remain server errors and should be investigated in server logs.

Imports are atomic; API product import expects a JSON array of product creation records, and demand import expects `{product_id,day,quantity}` rows. CSV parsing happens in the browser. Historical demand dates must precede today and forecast input must be consecutive daily observations. Reading timestamps are normalized to UTC and must increase per sensor. Sensors without fresh data appear missing after 45 minutes.
