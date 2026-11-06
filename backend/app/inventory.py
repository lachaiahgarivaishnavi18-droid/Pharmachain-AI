from datetime import date
from fastapi import HTTPException
from sqlalchemy import select, update
from .models import Batch, Product, Warehouse, InventoryTransaction, AuditLog, SystemConfiguration

def audit(db, actor, action, entity, detail):
    db.add(AuditLog(actor=actor, action=action, entity=str(entity), detail=detail))

def require(db, cls, identifier):
    item = db.get(cls, identifier)
    if item is None:
        raise HTTPException(404, f'{cls.__name__} not found')
    return item

def available(batch):
    return max(0, batch.quantity - batch.reserved) if batch.status == 'available' and batch.expiry_date > date.today() else 0

def summary(db, product_id=None):
    products = db.scalars(select(Product).where(Product.id == product_id) if product_id else select(Product)).all()
    batches = db.scalars(select(Batch)).all()
    result = []
    config = db.scalar(select(SystemConfiguration).where(SystemConfiguration.key == 'general'))
    near_expiry_days = config.value.get('near_expiry_days', 90) if config else 90
    for product in products:
        stock = [b for b in batches if b.product_id == product.id]
        usable = sum(available(b) for b in stock)
        result.append({'product_id': product.id, 'name': product.name, 'category': product.category, 'criticality': product.criticality,
                       'available': usable, 'total': sum(b.quantity for b in stock), 'reserved': sum(b.reserved for b in stock),
                       'quarantined': sum(b.quantity for b in stock if b.status == 'quarantined'),
                       'expired': sum(b.quantity for b in stock if b.expiry_date <= date.today()),
                       'near_expiry': sum(available(b) for b in stock if 0 < (b.expiry_date-date.today()).days <= near_expiry_days),
                       'min_stock': product.min_stock, 'max_stock': product.max_stock,
                       'status': 'low' if usable < product.reorder_point else 'excess' if usable > product.max_stock else 'healthy',
                       'unit_cost': product.unit_cost})
    return result

def capacity_check(db, warehouse_id, quantity, cold=False):
    wh = require(db, Warehouse, warehouse_id)
    # Lock warehouse on PostgreSQL to serialize capacity-changing transactions.
    db.execute(select(Warehouse).where(Warehouse.id == warehouse_id).with_for_update())
    stock = db.scalars(select(Batch).where(Batch.warehouse_id == warehouse_id)).all()
    if sum(b.quantity for b in stock) + quantity > wh.capacity:
        raise HTTPException(409, 'Warehouse capacity exceeded')
    if cold:
        cold_ids = set(db.scalars(select(Product.id).where(Product.temperature_sensitive.is_(True))).all())
        if sum(b.quantity for b in stock if b.product_id in cold_ids) + quantity > wh.cold_capacity:
            raise HTTPException(409, 'Cold-storage capacity exceeded')

def stock_in(db, data, actor):
    p = require(db, Product, data.product_id)
    capacity_check(db, data.warehouse_id, data.quantity, p.temperature_sensitive)
    batch = Batch(**data.model_dump())
    db.add(batch)
    db.flush()
    db.add(InventoryTransaction(batch_id=batch.id, kind='stock-in', quantity=data.quantity, actor=actor, reference='manual stock receipt'))
    audit(db, actor, 'stock-in', batch.id, data.model_dump(mode='json'))
    return batch

def allocate(db, data, actor, destination_id=None):
    require(db, Product, data.product_id)
    if destination_id == data.warehouse_id:
        raise HTTPException(422, 'Destination must differ from origin')
    candidates = db.scalars(select(Batch).where(Batch.product_id == data.product_id, Batch.warehouse_id == data.warehouse_id,
                                               Batch.status == 'available', Batch.expiry_date > date.today()).order_by(Batch.expiry_date, Batch.id).with_for_update()).all()
    if sum(available(b) for b in candidates) < data.quantity:
        raise HTTPException(409, 'Insufficient usable stock; expired, reserved and quarantined stock is excluded')
    if destination_id:
        p = require(db, Product, data.product_id)
        capacity_check(db, destination_id, data.quantity, p.temperature_sensitive)
    remaining, allocations = data.quantity, []
    for b in candidates:
        take = min(available(b), remaining)
        if not take:
            continue
        changed = db.execute(update(Batch).where(Batch.id == b.id, Batch.quantity >= take + b.reserved, Batch.status == 'available').values(quantity=Batch.quantity-take))
        if changed.rowcount != 1:
            raise HTTPException(409, 'Concurrent stock change; retry transaction')
        db.add(InventoryTransaction(batch_id=b.id, kind='transfer-out' if destination_id else 'stock-out', quantity=-take, actor=actor, reference=data.reference))
        if destination_id:
            target = db.scalar(select(Batch).where(Batch.number == b.number, Batch.product_id == b.product_id, Batch.warehouse_id == destination_id).with_for_update())
            if target and target.status != 'available':
                raise HTTPException(409, 'Destination batch is unavailable')
            if target:
                target.quantity += take
            else:
                target = Batch(number=b.number, product_id=b.product_id, warehouse_id=destination_id, quantity=take, reserved=0, manufacturing_date=b.manufacturing_date, expiry_date=b.expiry_date, status='available')
                db.add(target)
                db.flush()
            db.add(InventoryTransaction(batch_id=target.id, kind='transfer-in', quantity=take, actor=actor, reference=data.reference))
        allocations.append({'batch_id': b.id, 'batch': b.number, 'quantity': take})
        remaining -= take
        if not remaining:
            break
    audit(db, actor, 'transfer' if destination_id else 'stock-out', data.product_id, {'allocations': allocations, 'reference': data.reference})
    return allocations
