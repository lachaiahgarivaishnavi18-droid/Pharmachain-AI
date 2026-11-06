import os, io, csv, json, asyncio
from pathlib import Path
from datetime import date, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError, OperationalError
from fastapi.encoders import jsonable_encoder
from .database import Base, engine, get_db, SessionLocal
from .models import *
from .schemas import *
from .auth import current_user, roles, token, verify_password, hash_password
from .inventory import require, summary, stock_in, allocate, audit
from .forecasting import run_forecast
from .optimization import recommendation
from .cold_chain import ingest, sensor_health
from .agents import AGENTS, execute

@asynccontextmanager
async def lifespan(app):
    if os.getenv('AUTO_CREATE_SCHEMA', 'true').lower() == 'true': Base.metadata.create_all(engine)
    if os.getenv('SEED_DEMO', 'true').lower() == 'true':
        from .seed import seed
        with SessionLocal() as db: seed(db)
    # In-process jobs do not survive a restart; record interruption honestly.
    with SessionLocal() as db:
        for run in db.scalars(select(RLTrainingRun).where(RLTrainingRun.status.in_(['queued', 'running']))).all():
            run.status, run.result = 'interrupted', {'error': 'Backend restarted before job completion; submit a new job'}
        db.commit()
    task = None
    interval = int(os.getenv('ANALYSIS_INTERVAL_SECONDS', '0'))
    if interval >= 60:
        async def schedule():
            while True:
                await asyncio.sleep(interval)
                def analyze():
                    with SessionLocal() as db:
                        try:
                            execute(db, int(os.getenv('ANALYSIS_PRODUCT_ID', '1'))); db.commit()
                        except Exception:
                            db.rollback()
                await asyncio.to_thread(analyze)
        task = asyncio.create_task(schedule())
    try:
        yield
    finally:
        if task:
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass

app = FastAPI(title='PharmaChain AI', version='0.1.0', lifespan=lifespan, description='Synthetic research demonstration. No automated pharmaceutical disposition or supplier communication.')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_credentials=False, allow_methods=['GET','POST','PUT','DELETE'], allow_headers=['Authorization','Content-Type'])
read = Depends(current_user)
write = Depends(roles('operator', 'manager', 'admin'))
manage = Depends(roles('manager', 'admin'))

@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return Response(content=json.dumps({'detail': 'Record violates a uniqueness, reference or data constraint'}), status_code=409, media_type='application/json')

@app.exception_handler(OperationalError)
async def operational_error(request, exc):
    return Response(content=json.dumps({'detail': 'Database temporarily unavailable or busy; retry'}), status_code=503, media_type='application/json')

def page(db, cls, offset=0, limit=100):
    return db.scalars(select(cls).order_by(cls.id).offset(offset).limit(limit)).all()

@app.post('/api/auth/login')
def login(data: Login, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if not user or not verify_password(data.password, user.password_hash): raise HTTPException(401, 'Invalid credentials')
    return {'access_token': token(user), 'token_type': 'bearer', 'user': {'username': user.username, 'role': user.role}}

@app.get('/api/auth/me')
def me(user=read): return {'username': user.username, 'role': user.role}

@app.get('/api/health')
def health(): return {'status': 'ok', 'mode': 'synthetic research demo'}

@app.get('/api/health/database')
def db_health(user=read, db=Depends(get_db)):
    db.execute(text('SELECT 1')); return {'status': 'ok', 'dialect': engine.dialect.name}

@app.get('/api/health/models')
def model_health(user=read, db=Depends(get_db)):
    return {'rl_models': len(page(db, RLModel)), 'forecast': 'available', 'llm': 'deterministic explanations; no paid key required', 'training_enabled': os.getenv('RL_TRAINING_ENABLED','true').lower() == 'true'}

@app.get('/api/products')
def products(q: str = '', offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), user=read, db=Depends(get_db)):
    return db.scalars(select(Product).where(Product.name.ilike(f'%{q}%')).order_by(Product.id).offset(offset).limit(limit)).all()

@app.post('/api/products', status_code=201)
def create_product(data: ProductInput, user=write, db=Depends(get_db)):
    p = Product(**data.model_dump()); db.add(p); db.flush(); audit(db, user.username, 'create-product', p.id, data.model_dump()); return p

@app.get('/api/products/{product_id}')
def get_product(product_id: int, user=read, db=Depends(get_db)): return require(db, Product, product_id)

@app.put('/api/products/{product_id}')
def update_product(product_id: int, data: ProductInput, user=manage, db=Depends(get_db)):
    p = require(db, Product, product_id)
    for k,v in data.model_dump().items(): setattr(p,k,v)
    audit(db, user.username, 'update-product', p.id, data.model_dump()); return p

@app.delete('/api/products/{product_id}')
def delete_product(product_id: int, user=manage, db=Depends(get_db)):
    p = require(db, Product, product_id); audit(db,user.username,'delete-product',p.id,{'name':p.name}); db.delete(p); db.flush(); return {'deleted': True}

@app.get('/api/warehouses')
def warehouses(user=read, db=Depends(get_db)): return page(db, Warehouse)

@app.post('/api/warehouses',status_code=201)
def add_warehouse(data:WarehouseInput,user=manage,db=Depends(get_db)):
    row=Warehouse(**data.model_dump());db.add(row);db.flush();audit(db,user.username,'create-warehouse',row.id,data.model_dump());return row

@app.post('/api/inventory/batches/{batch_id}/adjust')
def adjust_batch(batch_id:int,data:BatchAdjustment,user=manage,db=Depends(get_db)):
    from .inventory import capacity_check
    b=db.scalar(select(Batch).where(Batch.id==batch_id).with_for_update())
    if not b:raise HTTPException(404,'Batch not found')
    if b.status=='quarantined' and data.quantity != b.quantity:raise HTTPException(409,'Quarantined quantity changes require an external authorized quality disposition procedure')
    delta=data.quantity-b.quantity
    if delta>0:capacity_check(db,b.warehouse_id,delta,db.get(Product,b.product_id).temperature_sensitive)
    old={'quantity':b.quantity,'reserved':b.reserved,'status':b.status}
    b.quantity,b.reserved=data.quantity,data.reserved
    db.add(InventoryTransaction(batch_id=b.id,kind='adjustment',quantity=delta,actor=user.username,reference=data.reason))
    audit(db,user.username,'adjust-batch',b.id,{'before':old,'after':data.model_dump()});return b

@app.get('/api/inventory')
def inventory(status: str | None = None, user=read, db=Depends(get_db)):
    rows = summary(db); return [x for x in rows if not status or x['status'] == status]

@app.get('/api/inventory/batches')
def batches(product_id: int | None = None, warehouse_id: int | None = None, user=read, db=Depends(get_db)):
    query = select(Batch)
    if product_id: query = query.where(Batch.product_id == product_id)
    if warehouse_id: query = query.where(Batch.warehouse_id == warehouse_id)
    return db.scalars(query.order_by(Batch.expiry_date)).all()

@app.get('/api/inventory/low-stock')
def low_stock(user=read, db=Depends(get_db)): return [x for x in summary(db) if x['status'] == 'low']

@app.get('/api/inventory/near-expiry')
def near_expiry(days: int = Query(90, ge=1, le=365), user=read, db=Depends(get_db)):
    return db.scalars(select(Batch).where(Batch.expiry_date <= date.today()+timedelta(days=days), Batch.quantity > 0).order_by(Batch.expiry_date)).all()

@app.get('/api/inventory/transactions')
def transactions(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), user=read, db=Depends(get_db)): return page(db, InventoryTransaction, offset, limit)

@app.get('/api/inventory/{product_id}')
def product_inventory(product_id: int, user=read, db=Depends(get_db)):
    require(db, Product, product_id); return summary(db, product_id)[0]

@app.post('/api/inventory/stock-in', status_code=201)
def add_stock(data: BatchInput, user=write, db=Depends(get_db)): return stock_in(db, data, user.username)

@app.post('/api/inventory/stock-out')
def remove_stock(data: StockOut, user=write, db=Depends(get_db)): return {'allocations': allocate(db, data, user.username)}

@app.post('/api/inventory/transfer')
def transfer(data: Transfer, user=write, db=Depends(get_db)): return {'allocations': allocate(db, data, user.username, data.destination_id)}

@app.post('/api/forecast/run')
def forecast_run(data: ForecastInput, user=write, db=Depends(get_db)):
    require(db,Product,data.product_id); return run_forecast(db, data.product_id, data.horizon, data.advanced)

@app.get('/api/forecast')
def forecasts(user=read, db=Depends(get_db)): return page(db, DemandForecast)

@app.get('/api/forecast/metrics')
def forecast_metrics(user=read, db=Depends(get_db)): return page(db, ForecastEvaluation)

@app.get('/api/forecast/{product_id}')
def forecast_get(product_id: int, user=read, db=Depends(get_db)):
    f = db.scalar(select(DemandForecast).where(DemandForecast.product_id == product_id).order_by(DemandForecast.id.desc()).limit(1))
    return f.result if f else None

@app.post('/api/rl/train', status_code=202)
def train(data: TrainInput, background: BackgroundTasks, user=manage, db=Depends(get_db)):
    if os.getenv('RL_TRAINING_ENABLED','true').lower() != 'true':
        raise HTTPException(503,'PPO/DQN training runs on your local workstation. The hosted app supports saved-policy inference and reproducible evaluation; see the project README for training commands.')
    active = db.scalar(select(RLTrainingRun).where(RLTrainingRun.status.in_(['queued','running'])))
    if active: raise HTTPException(409, 'A training job is already active')
    run = RLTrainingRun(config=data.model_dump()); db.add(run); db.flush(); db.commit()
    from .jobs import training_job
    background.add_task(training_job, run.id)
    audit(db,user.username,'train-policy',run.id,data.model_dump()); return run

@app.post('/api/rl/recommend')
def rl_recommend(data: RecommendInput, user=write, db=Depends(get_db)): return recommendation(db, data.product_id)

@app.post('/api/rl/evaluate')
def rl_evaluate(user=manage, db=Depends(get_db)):
    from rl.evaluation.compare_baselines import evaluate
    model = db.scalar(select(RLModel).order_by(RLModel.id.desc()).limit(1))
    result = evaluate(model.path if model else None, model.algorithm if model else 'PPO'); db.add(RLPolicyEvaluation(result=result)); return result

@app.get('/api/rl/models')
def rl_models(user=read, db=Depends(get_db)):
    return [{'id': m.id, 'version': m.version, 'algorithm': m.algorithm, 'training_run_id': m.training_run_id} for m in page(db,RLModel)]

@app.get('/api/rl/training-history')
def rl_history(user=read, db=Depends(get_db)): return page(db,RLTrainingRun)

@app.get('/api/rl/policy-performance')
def rl_performance(user=read, db=Depends(get_db)):
    row = db.scalar(select(RLPolicyEvaluation).order_by(RLPolicyEvaluation.id.desc()).limit(1)); return row.result if row else None

@app.post('/api/cold-chain/readings', status_code=201)
def add_reading(data: ReadingInput, user=write, db=Depends(get_db)): return ingest(db,data,user.username)

@app.get('/api/cold-chain/readings')
def readings(sensor_id: int | None = None, limit: int = Query(500, ge=1, le=5000), user=read, db=Depends(get_db)):
    query = select(TemperatureReading)
    if sensor_id: query = query.where(TemperatureReading.sensor_id == sensor_id)
    return list(reversed(db.scalars(query.order_by(TemperatureReading.timestamp.desc()).limit(limit)).all()))

@app.get('/api/cold-chain/sensors')
def sensors(user=read, db=Depends(get_db)): return sensor_health(db)

@app.post('/api/cold-chain/sensors',status_code=201)
def add_sensor(data:SensorInput,user=manage,db=Depends(get_db)):
    require(db,Product,data.product_id)
    if data.warehouse_id:require(db,Warehouse,data.warehouse_id)
    if data.shipment_id:require(db,Shipment,data.shipment_id)
    row=TemperatureSensor(**data.model_dump());db.add(row);db.flush();audit(db,user.username,'create-sensor',row.id,data.model_dump());return row

@app.get('/api/cold-chain/warehouses')
def cold_warehouses(user=read, db=Depends(get_db)): return page(db,Warehouse)

@app.get('/api/cold-chain/shipments')
def shipments(user=read, db=Depends(get_db)): return page(db,Shipment)

@app.get('/api/cold-chain/alerts')
def alerts(user=read, db=Depends(get_db)): return db.scalars(select(ColdChainAlert).order_by(ColdChainAlert.id.desc())).all()

@app.get('/api/cold-chain/excursions')
def excursions(user=read, db=Depends(get_db)): return page(db,TemperatureExcursion)

@app.post('/api/cold-chain/alerts/{alert_id}/investigate')
def investigate(alert_id: int, data: Decision, user=Depends(roles('quality','admin')), db=Depends(get_db)):
    a = require(db, ColdChainAlert, alert_id); a.status, a.investigation = 'investigating', data.reason
    audit(db,user.username,'investigate-alert',a.id,{'note':data.reason}); return a

@app.get('/api/suppliers')
def suppliers(user=read, db=Depends(get_db)): return page(db,Supplier)

@app.post('/api/suppliers', status_code=201)
def add_supplier(data: SupplierInput, user=manage, db=Depends(get_db)):
    s=Supplier(**data.model_dump()); db.add(s); db.flush(); audit(db,user.username,'create-supplier',s.id,data.model_dump()); return s

@app.get('/api/suppliers/{supplier_id}')
def get_supplier(supplier_id:int,user=read,db=Depends(get_db)):
    return {'supplier':require(db,Supplier,supplier_id),'catalog':db.scalars(select(SupplierProduct).where(SupplierProduct.supplier_id==supplier_id)).all()}

@app.post('/api/suppliers/{supplier_id}/catalog',status_code=201)
def add_catalog(supplier_id:int,data:CatalogInput,user=manage,db=Depends(get_db)):
    require(db,Supplier,supplier_id);require(db,Product,data.product_id)
    existing=db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id==supplier_id,SupplierProduct.product_id==data.product_id))
    if existing:raise HTTPException(409,'Supplier product mapping already exists')
    row=SupplierProduct(supplier_id=supplier_id,**data.model_dump());db.add(row);db.flush();audit(db,user.username,'add-catalog-product',row.id,data.model_dump());return row

@app.put('/api/suppliers/{supplier_id}')
def update_supplier(supplier_id:int,data:SupplierInput,user=manage,db=Depends(get_db)):
    s=require(db,Supplier,supplier_id)
    for k,v in data.model_dump().items():setattr(s,k,v)
    audit(db,user.username,'update-supplier',s.id,data.model_dump()); return s

@app.post('/api/purchase-orders', status_code=201)
def create_order(data: OrderInput, user=write, db=Depends(get_db)):
    supplier = require(db,Supplier,data.supplier_id); lines=[]
    if len({i.product_id for i in data.items}) != len(data.items): raise HTTPException(422,'Duplicate product lines')
    for item in data.items:
        mapping=db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id==supplier.id,SupplierProduct.product_id==item.product_id))
        if not mapping or item.quantity < mapping.minimum_order: raise HTTPException(422,'Product is not in supplier catalog or quantity is below MOQ')
        lines.append((item,mapping.unit_cost))
    order=PurchaseOrder(supplier_id=supplier.id,total=round(sum(i.quantity*c for i,c in lines),2),expected_date=date.today()+timedelta(days=supplier.lead_days),requested_by=user.username)
    db.add(order);db.flush()
    for i,c in lines:db.add(PurchaseOrderItem(order_id=order.id,product_id=i.product_id,quantity=i.quantity,unit_cost=c))
    audit(db,user.username,'draft-purchase-order',order.id,data.model_dump()); return order

@app.get('/api/purchase-orders')
def orders(user=read,db=Depends(get_db)):return db.scalars(select(PurchaseOrder).order_by(PurchaseOrder.id.desc())).all()

@app.get('/api/purchase-orders/{order_id}')
def order_detail(order_id:int,user=read,db=Depends(get_db)):
    return {'order':require(db,PurchaseOrder,order_id),'items':db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id==order_id)).all()}

def decide_order(db, order_id, user, decision, reason):
    order=db.scalar(select(PurchaseOrder).where(PurchaseOrder.id==order_id).with_for_update())
    if not order:raise HTTPException(404,'Purchase order not found')
    if order.status != 'draft':raise HTTPException(409,'Only draft orders can be decided')
    order.status,order.approved_by=decision,user.username
    db.add(HumanApproval(order_id=order.id,actor=user.username,decision=decision,reason=reason))
    audit(db,user.username,decision+'-purchase-order',order.id,{'reason':reason,'total':order.total})
    return order

@app.post('/api/purchase-orders/{order_id}/approve')
def approve_order(order_id:int,data:Decision,user=manage,db=Depends(get_db)):return decide_order(db,order_id,user,'approved',data.reason)

@app.post('/api/purchase-orders/{order_id}/reject')
def reject_order(order_id:int,data:Decision,user=manage,db=Depends(get_db)):return decide_order(db,order_id,user,'rejected',data.reason)

@app.get('/api/agents')
def agents(user=read):return [{'id':k,'name':n,'purpose':p} for k,n,p in AGENTS]

@app.post('/api/agents/run')
def run_agents(data:RecommendInput,user=write,db=Depends(get_db)):
    require(db,Product,data.product_id); return execute(db,data.product_id)

@app.get('/api/agents/executions')
def executions(run_id:str|None=None,user=read,db=Depends(get_db)):
    q=select(AgentExecution)
    if run_id:q=q.where(AgentExecution.run_id==run_id)
    return db.scalars(q.order_by(AgentExecution.id.desc()).limit(200)).all()

@app.get('/api/agents/executions/{execution_id}')
def execution_detail(execution_id:int,user=read,db=Depends(get_db)):return require(db,AgentExecution,execution_id)

@app.get('/api/analytics/dashboard')
def dashboard(user=read,db=Depends(get_db)):
    rows=summary(db)
    return {'synthetic':True,'products':len(rows),'available_units':sum(r['available'] for r in rows),'inventory_value':round(sum(r['available']*r['unit_cost'] for r in rows),2),
            'low_stock':sum(r['status']=='low' for r in rows),'near_expiry':sum(r['near_expiry'] for r in rows),'quarantined':sum(r['quarantined'] for r in rows),
            'open_alerts':db.scalar(select(func.count()).select_from(ColdChainAlert).where(ColdChainAlert.status=='open')),
            'pending_approvals':db.scalar(select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.status=='draft')),
            'risk_products':[r for r in rows if r['status']!='healthy' or r['near_expiry'] or r['quarantined']],
            'categories':[{'name':c,'value':sum(r['available'] for r in rows if r['category']==c)} for c in sorted(set(r['category'] for r in rows))]}

@app.get('/api/analytics/inventory')
def inventory_analytics(user=read,db=Depends(get_db)):return summary(db)

@app.get('/api/analytics/cold-chain')
def cold_analytics(user=read,db=Depends(get_db)):return {'sensors':sensor_health(db),'excursions':page(db,TemperatureExcursion)}

@app.get('/api/analytics/rl')
def rl_analytics(user=read,db=Depends(get_db)):return rl_performance(user,db)

@app.get('/api/risks')
def risks(user=read,db=Depends(get_db)):return page(db,RiskAssessment)

@app.get('/api/settings')
def settings(user=read,db=Depends(get_db)):return page(db,SystemConfiguration)

@app.put('/api/settings')
def update_settings(data:dict,user=Depends(roles('admin')),db=Depends(get_db)):
    if set(data)-{'near_expiry_days','retention_days'}:raise HTTPException(422,'Only near_expiry_days and retention_days are editable')
    if any(type(v)!=int or not 1<=v<=3650 for v in data.values()):raise HTTPException(422,'Settings must be integers between 1 and 3650')
    row=db.scalar(select(SystemConfiguration).where(SystemConfiguration.key=='general'))
    row.value={**row.value,**data};audit(db,user.username,'update-settings',row.id,data);return row

@app.get('/api/users')
def users(user=Depends(roles('admin')),db=Depends(get_db)):return [{'id':u.id,'username':u.username,'role':u.role} for u in page(db,User)]

@app.post('/api/users',status_code=201)
def create_user(data:UserInput,user=Depends(roles('admin')),db=Depends(get_db)):
    u=User(username=data.username,password_hash=hash_password(data.password),role=data.role);db.add(u);db.flush();audit(db,user.username,'create-user',u.id,{'username':u.username,'role':u.role});return {'id':u.id,'username':u.username,'role':u.role}

@app.get('/api/audit')
def audit_logs(user=manage,db=Depends(get_db)):return db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200)).all()

@app.get('/api/export/{kind}')
def export(kind:str,format:str='csv',user=read,db=Depends(get_db)):
    sources={'inventory':lambda:summary(db),'products':lambda:page(db,Product,0,10000),'batches':lambda:page(db,Batch,0,10000),'demand':lambda:page(db,DemandHistory,0,100000),'readings':lambda:page(db,TemperatureReading,0,100000),'shipments':lambda:page(db,Shipment,0,10000)}
    if kind not in sources:raise HTTPException(404,'Unknown export dataset')
    records=jsonable_encoder(sources[kind]())
    if format=='json':content=json.dumps({'synthetic':True,'records':records},indent=2);media='application/json'
    elif format=='csv':
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(records[0]) if records else ['empty']);writer.writeheader();writer.writerows(records);content=stream.getvalue();media='text/csv'
    elif format=='pdf':
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        buffer=io.BytesIO();c=canvas.Canvas(buffer,pagesize=A4)
        c.setFont('Helvetica-Bold',16);c.drawString(40,800,'PharmaChain AI | Synthetic research report');c.setFont('Helvetica',9);y=775
        for row in records:
            line=' | '.join(f'{k}: {v}' for k,v in row.items() if k in ['name','available','total','status','quarantined','near_expiry','product_id'])
            c.drawString(40,y,line[:115]);y-=16
            if y<45:c.showPage();c.setFont('Helvetica',9);y=800
        c.save();content=buffer.getvalue();media='application/pdf'
    else:raise HTTPException(422,'Use csv, json or pdf')
    return Response(content=content,media_type=media,headers={'Content-Disposition':f'attachment; filename="pharmachain-synthetic-{kind}.{format}"'})

@app.post('/api/import/products')
def import_products(data:list[ProductInput],user=manage,db=Depends(get_db)):
    if len(data)>1000:raise HTTPException(422,'Maximum 1000 products per import')
    result=[]
    for item in data:
        p=Product(**item.model_dump());db.add(p);db.flush();result.append(p.id)
    audit(db,user.username,'import-products','products',{'ids':result});return {'created':len(result),'ids':result}

@app.post('/api/import/demand')
def import_demand(data:list[dict],user=manage,db=Depends(get_db)):
    if len(data)>50000:raise HTTPException(422,'Maximum 50000 rows per import')
    for row in data:
        try:
            pid=int(row['product_id']);day=date.fromisoformat(row['day']);quantity=int(row['quantity'])
            if quantity<0 or day>=date.today():raise ValueError()
        except (KeyError,ValueError,TypeError):raise HTTPException(422,'Demand rows require product_id, past ISO day and nonnegative integer quantity')
        require(db,Product,pid);db.add(DemandHistory(product_id=pid,day=day,quantity=quantity))
    db.flush();audit(db,user.username,'import-demand','demand',{'rows':len(data)});return {'created':len(data)}
