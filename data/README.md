# Synthetic demonstration data

The deterministic seed (`backend/app/seed.py`, RNG seed 42) creates 50 named pharmaceutical products, 5 warehouses, 10 suppliers, 100 supplier mappings, 150 batches, 600 historical simulation ledger rows, 18,250 daily demand observations (365 days/product), 10 shipments, 10 sensors and 480 temperature readings. Two sensors have scripted excursions. Stock includes shortages, excess, near-expiry, expired and quarantined batches. Dates are relative to seed execution time.

All names, quantities, costs, temperature behavior and logistical records are synthetic. Product storage settings are example configurations, not authoritative label instructions. Historical transaction rows are independent simulated examples, not a reconciliation of current opening balances. New stock changes are audited and transactionally consistent. Seeding runs once when the user table is empty; subsequent starts preserve edits.

Export after startup:

```powershell
.\.venv\Scripts\python.exe -m scripts.export-demo
```

Exports appear in ignored `data/exports/` as CSV and JSON. API exports also cover products, inventory, batches, demand, readings and shipments. JSON exports include `synthetic:true`. CSV download filenames explicitly label synthetic data. Product/demand import accepts validated JSON arrays, and the Settings interface converts CSV into JSON. Product import uses the creation schema (omit exported IDs/timestamps); demand import uses `product_id,day,quantity` only. Duplicate product/day demand records are rejected atomically. Sensor readings must arrive in increasing UTC timestamp order. Real device integration must authenticate upstream devices and call the ingestion interface with `source=device`; no real devices are connected.
