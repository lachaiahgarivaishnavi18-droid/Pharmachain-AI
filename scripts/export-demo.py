"""Export the seeded synthetic database to portable JSON and CSV datasets."""
import csv,json
from pathlib import Path
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from backend.app.database import SessionLocal
from backend.app.models import Product,Warehouse,Supplier,Batch,DemandHistory,TemperatureReading,Shipment,InventoryTransaction

out=Path('data/exports');out.mkdir(parents=True,exist_ok=True)
with SessionLocal() as db:
    for cls in [Product,Warehouse,Supplier,Batch,DemandHistory,TemperatureReading,Shipment,InventoryTransaction]:
        rows=jsonable_encoder(db.scalars(select(cls)).all())
        (out/f'{cls.__tablename__}.json').write_text(json.dumps({'synthetic':True,'records':rows},indent=2))
        if rows:
            with (out/f'{cls.__tablename__}.csv').open('w',newline='',encoding='utf-8') as stream:
                writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
        print(cls.__tablename__,len(rows))
