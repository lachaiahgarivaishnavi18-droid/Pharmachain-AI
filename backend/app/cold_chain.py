from datetime import timedelta, timezone
from sqlalchemy import select
from fastapi import HTTPException
from .models import *
from .inventory import require, audit

def ingest(db, data, actor):
    sensor = require(db, TemperatureSensor, data.sensor_id)
    product = require(db, Product, sensor.product_id)
    timestamp = data.timestamp.astimezone(timezone.utc).replace(tzinfo=None) if data.timestamp.tzinfo else data.timestamp
    if timestamp > now()+timedelta(minutes=5):
        raise HTTPException(422, 'Sensor timestamp is in the future')
    latest = db.scalar(select(TemperatureReading).where(TemperatureReading.sensor_id == sensor.id).order_by(TemperatureReading.timestamp.desc()).limit(1))
    if latest and timestamp <= latest.timestamp:
        raise HTTPException(409, 'Readings must arrive in strictly increasing timestamp order')
    reading = TemperatureReading(**{**data.model_dump(), 'timestamp': timestamp})
    db.add(reading)
    sensor.status = data.sensor_status
    if data.sensor_status == 'failed':
        db.add(ColdChainAlert(sensor_id=sensor.id, message='Sensor failure: investigate coverage gap', severity='high'))
    if latest and timestamp-latest.timestamp > timedelta(minutes=45):
        db.add(ColdChainAlert(sensor_id=sensor.id, message='Missing sensor readings: gap exceeds 45 minutes', severity='medium'))
    excursion = db.scalar(select(TemperatureExcursion).where(TemperatureExcursion.sensor_id == sensor.id, TemperatureExcursion.ended_at.is_(None)).with_for_update())
    outside = not product.temp_min <= data.temperature <= product.temp_max
    if outside and data.sensor_status == 'healthy':
        if not excursion:
            if sensor.warehouse_id:
                batches = db.scalars(select(Batch).where(Batch.warehouse_id == sensor.warehouse_id, Batch.product_id == product.id)).all()
            else:
                batches = db.scalars(select(Batch).join(ShipmentItem, ShipmentItem.batch_id == Batch.id).where(ShipmentItem.shipment_id == sensor.shipment_id)).all()
            excursion = TemperatureExcursion(sensor_id=sensor.id, started_at=timestamp, minimum=data.temperature, maximum=data.temperature, affected_batches=[b.id for b in batches])
            db.add(excursion); db.flush()
            for b in batches:
                b.status = 'quarantined'
            db.add(ColdChainAlert(sensor_id=sensor.id, excursion_id=excursion.id, message=f'{product.name}: outside configured {product.temp_min}–{product.temp_max} °C. Affected stock quarantined pending authorized quality review.'))
            audit(db, actor, 'excursion-quarantine', sensor.id, {'batch_ids': excursion.affected_batches})
        excursion.minimum = min(excursion.minimum, data.temperature)
        excursion.maximum = max(excursion.maximum, data.temperature)
        excursion.duration_minutes = (timestamp-excursion.started_at).total_seconds()/60
    elif excursion and data.sensor_status == 'healthy':
        excursion.ended_at = timestamp
        excursion.duration_minutes = (timestamp-excursion.started_at).total_seconds()/60
    db.flush()
    return reading

def sensor_health(db):
    result = []
    for sensor in db.scalars(select(TemperatureSensor)).all():
        latest = db.scalar(select(TemperatureReading).where(TemperatureReading.sensor_id == sensor.id).order_by(TemperatureReading.timestamp.desc()).limit(1))
        p = db.get(Product, sensor.product_id)
        result.append({'id': sensor.id, 'name': sensor.name, 'product': p.name, 'temp_min': p.temp_min, 'temp_max': p.temp_max, 'temperature': latest.temperature if latest else None, 'timestamp': latest.timestamp.isoformat() if latest else None,
                       'status': 'missing' if not latest or now()-latest.timestamp > timedelta(minutes=45) else sensor.status,
                       'excursion': bool(latest and not p.temp_min <= latest.temperature <= p.temp_max)})
    return result
