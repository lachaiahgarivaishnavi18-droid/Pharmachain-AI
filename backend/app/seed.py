import os, math, random
from datetime import date, timedelta
from sqlalchemy import select
from .models import *
from .auth import hash_password

PRODUCT_NAMES = ['Insulin glargine', 'Hepatitis B vaccine', 'Adalimumab', 'Erythropoietin', 'Rituximab', 'Influenza vaccine', 'Filgrastim', 'Somatropin', 'Oxytocin', 'Immunoglobulin', 'Amoxicillin', 'Paracetamol', 'Metformin', 'Atorvastatin', 'Amlodipine', 'Omeprazole', 'Losartan', 'Azithromycin', 'Cefixime', 'Cetirizine', 'Doxycycline', 'Pantoprazole', 'Salbutamol', 'Montelukast', 'Clopidogrel', 'Aspirin', 'Levothyroxine', 'Prednisolone', 'Furosemide', 'Spironolactone', 'Warfarin', 'Enoxaparin', 'Ondansetron', 'Domperidone', 'Fluconazole', 'Acyclovir', 'Levetiracetam', 'Gabapentin', 'Sertraline', 'Escitalopram', 'Risperidone', 'Olanzapine', 'Carbamazepine', 'Sodium valproate', 'Ciprofloxacin', 'Levofloxacin', 'Vancomycin', 'Meropenem', 'Ceftriaxone', 'Human albumin']

def seed(db):
    if db.scalar(select(User.id).limit(1)):
        return
    rng = random.Random(42)
    today = date.today()
    password = os.getenv('DEMO_PASSWORD')
    if not password or len(password) < 12:
        raise ValueError('Set DEMO_PASSWORD to a password of at least 12 characters before initializing demo users')
    for role in ['admin', 'manager', 'operator', 'quality', 'viewer']:
        db.add(User(username=role, password_hash=hash_password(password), role=role))
    for category in ['Biologics', 'Vaccines', 'General']:
        db.add(ProductCategory(name=category))
    warehouses = []
    for name, region in [('Mumbai Central', 'West'), ('Delhi Distribution', 'North'), ('Bengaluru Hub', 'South'), ('Hyderabad Cold Store', 'South'), ('Kolkata Regional', 'East')]:
        w = Warehouse(name=name, region=region, capacity=100000, cold_capacity=40000)
        db.add(w); warehouses.append(w)
    suppliers = []
    for i in range(10):
        s = Supplier(name=f'{["Aster", "Nova", "Helix", "Medline", "Zenith", "Cura", "Vertex", "LifeCore", "Synova", "Atlas"][i]} Pharma Supply', lead_days=3+i, reliability=.85+i*.014)
        db.add(s); suppliers.append(s)
    db.flush()
    products, batches = [], []
    for i, name in enumerate(PRODUCT_NAMES):
        cold = i < 10 or i == 49
        p = Product(name=name, generic_name=name, category='Vaccines' if 'vaccine' in name else 'Biologics' if cold else 'General', dosage_form='Injection' if cold else 'Tablet', strength='100 IU/ml' if i == 0 else '10 mg', temperature_sensitive=cold, temp_min=2 if cold else 15, temp_max=8 if cold else 25, min_stock=180, max_stock=3000, reorder_point=450, unit_cost=round(rng.uniform(5, 1500), 2), criticality='critical' if cold else 'standard')
        db.add(p); db.flush(); products.append(p)
        for j in range(3):
            qty = rng.randint(10, 60) if i % 7 == 0 else rng.randint(1100, 1600) if i % 11 == 0 else rng.randint(160, 600)
            expiry = today + timedelta(days=20+j*10 if i % 8 == 0 else 180+j*80)
            if i == 18 and j == 0: expiry = today-timedelta(days=3)
            b = Batch(number=f'SYN-{i+1:03d}-{j+1}', product_id=p.id, warehouse_id=warehouses[(i+j)%5].id, quantity=qty, reserved=0, manufacturing_date=today-timedelta(days=180), expiry_date=expiry, status='quarantined' if i == 2 and j == 0 else 'available')
            db.add(b); db.flush(); batches.append(b)
            for k in range(4):
                db.add(InventoryTransaction(batch_id=b.id, kind='synthetic-history', quantity=qty if k == 0 else -rng.randint(1, 10), actor='synthetic-seed', reference='Independent simulated historical ledger; not a reconciliation of opening balances'))
        for s in [suppliers[i % 10], suppliers[(i+1) % 10]]:
            db.add(SupplierProduct(supplier_id=s.id, product_id=p.id, unit_cost=p.unit_cost*(.95+rng.random()*.1), minimum_order=50))
        for day in range(365):
            t = today-timedelta(days=365-day)
            demand = max(0, round((20+i%12)* (1+.25*math.sin(day*2*math.pi/365)+.15*math.sin(day*2*math.pi/7))+rng.gauss(0, 4)))
            db.add(DemandHistory(product_id=p.id, day=t, quantity=demand))
    shipments = []
    for i in range(10):
        shipment = Shipment(reference=f'SYN-SHP-{1001+i}', origin=warehouses[i%5].name, destination=warehouses[(i+1)%5].name, status='delayed' if i%4 == 0 else 'in-transit', eta=now()+timedelta(hours=-3 if i%4 == 0 else 8+i))
        db.add(shipment); db.flush(); shipments.append(shipment)
        db.add(ShipmentItem(shipment_id=shipment.id, batch_id=batches[i*3].id, quantity=10))
    db.flush()
    from .cold_chain import ingest
    from .schemas import ReadingInput
    for i in range(10):
        sensor = TemperatureSensor(name=f'{"Refrigerator" if i < 5 else "Shipment logger"} {i+1:02d}', warehouse_id=warehouses[i%5].id if i < 5 else None, shipment_id=shipments[i].id if i >= 5 else None, product_id=products[i].id)
        db.add(sensor); db.flush()
        for j in range(48):
            temperature = 5+rng.gauss(0, .35)+(4.5 if i in [0, 6] and j > 40 else 0)
            ingest(db, ReadingInput(sensor_id=sensor.id, timestamp=now()-timedelta(minutes=(48-j)*15), temperature=temperature), 'synthetic-seed')
    db.add(SystemConfiguration(key='general', value={'near_expiry_days': 90, 'retention_days': 365, 'llm_provider': 'deterministic', 'synthetic': True}))
    db.commit()
