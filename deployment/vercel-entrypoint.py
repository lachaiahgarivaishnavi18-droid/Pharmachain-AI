"""Vercel ASGI entrypoint with persistent PostgreSQL and atomic demo bootstrap."""
import os,json,gzip
from pathlib import Path
from datetime import datetime,date
from contextlib import asynccontextmanager
from sqlalchemy import select,text,Date,DateTime
os.environ['AUTO_CREATE_SCHEMA']='false'
os.environ['SEED_DEMO']='false'
os.environ['RL_TRAINING_ENABLED']='false'
os.environ['ANALYSIS_INTERVAL_SECONDS']='0'
from backend.app.main import app
from backend.app.database import Base,engine
from backend.app.models import User

def bootstrap():
    if engine.dialect.name != 'postgresql':raise RuntimeError('Hosted deployment requires persistent PostgreSQL DATABASE_URL')
    # One initialization transaction across all cold starts; no per-instance SQLite fallback.
    with engine.begin() as connection:
        connection.execute(text('SELECT pg_advisory_xact_lock(742019031)'))
        Base.metadata.create_all(connection)
        if connection.scalar(select(User.id).limit(1)):return
        snapshot=json.loads(gzip.decompress((Path(__file__).resolve().parents[1]/'demo-snapshot.json.gz').read_bytes()))
        for table in Base.metadata.sorted_tables:
            records=snapshot.get(table.name,[])
            if not records:continue
            for row in records:
                for column in table.columns:
                    value=row.get(column.name)
                    if value is not None and isinstance(column.type,DateTime):row[column.name]=datetime.fromisoformat(value)
                    elif value is not None and isinstance(column.type,Date):row[column.name]=date.fromisoformat(value)
            connection.execute(table.insert(),records)
            connection.execute(text("SELECT setval(pg_get_serial_sequence(:table, 'id'), COALESCE((SELECT MAX(id) FROM "+table.name+"),1), true)"),{'table':table.name})

@asynccontextmanager
async def hosted_lifespan(application):
    bootstrap()
    yield

app.router.lifespan_context=hosted_lifespan
