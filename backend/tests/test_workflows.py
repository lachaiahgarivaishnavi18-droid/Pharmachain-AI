from datetime import date,timedelta
import numpy as np
import pytest
from sqlalchemy import select
from backend.app.models import Batch,DemandHistory,TemperatureSensor,TemperatureExcursion,ColdChainAlert,AgentExecution,Warehouse,AuditLog
from backend.app.optimization import eoq,safety_stock,reorder_point

def add_batch(client,headers,number='B1',quantity=100,days=60):
    return client.post('/api/inventory/stock-in',headers=headers(),json={'number':number,'product_id':1,'warehouse_id':1,'quantity':quantity,'manufacturing_date':str(date.today()-timedelta(days=30)),'expiry_date':str(date.today()+timedelta(days=days))})

def test_auth_and_role_boundaries(client,headers):
    assert client.post('/api/auth/login',json={'username':'admin','password':'wrong'}).status_code==401
    assert client.get('/api/products').status_code in [401,403]
    assert client.post('/api/products',headers=headers('viewer'),json={'name':'New medicine'}).status_code==403
    assert client.post('/api/products',headers=headers('operator'),json={'name':'New medicine'}).status_code==201

def test_product_validation_and_update(client,headers):
    assert client.post('/api/products',headers=headers(),json={'name':'Invalid','temp_min':10,'temp_max':2}).status_code==422
    assert client.put('/api/products/1',headers=headers(),json={'name':'Updated synthetic product'}).status_code==200
    assert client.get('/api/products/1',headers=headers()).json()['name']=='Updated synthetic product'

def test_fefo_and_unavailable_exclusion(client,headers,db):
    late=add_batch(client,headers,'LATE',100,120).json()
    early=add_batch(client,headers,'EARLY',50,30).json()
    db.add(Batch(number='QUAR',product_id=1,warehouse_id=1,quantity=900,reserved=0,status='quarantined',manufacturing_date=date.today()-timedelta(days=30),expiry_date=date.today()+timedelta(days=10)))
    db.add(Batch(number='EXPIRED',product_id=1,warehouse_id=1,quantity=500,reserved=0,status='available',manufacturing_date=date.today()-timedelta(days=30),expiry_date=date.today()-timedelta(days=1)))
    db.commit()
    result=client.post('/api/inventory/stock-out',headers=headers(),json={'product_id':1,'warehouse_id':1,'quantity':70,'reference':'test FEFO'})
    assert result.status_code==200,result.text
    assert [r['batch_id'] for r in result.json()['allocations']]==[early['id'],late['id']]
    stock=client.get('/api/inventory/1',headers=headers()).json()
    assert stock['available']==80 and stock['quarantined']==900 and stock['expired']==500
    assert client.post('/api/inventory/stock-out',headers=headers(),json={'product_id':1,'warehouse_id':1,'quantity':81,'reference':'oversell'}).status_code==409

def test_transfer_and_capacity(client,headers,db):
    assert add_batch(client,headers).status_code==201
    r=client.post('/api/inventory/transfer',headers=headers(),json={'product_id':1,'warehouse_id':1,'destination_id':2,'quantity':30,'reference':'transfer test'})
    assert r.status_code==200,r.text
    assert sum(b.quantity for b in db.scalars(select(Batch)).all())==100
    dest=db.get(Warehouse,2);dest.capacity=31;db.commit()
    assert client.post('/api/inventory/transfer',headers=headers(),json={'product_id':1,'warehouse_id':1,'destination_id':2,'quantity':5,'reference':'capacity test'}).status_code==409
    assert sum(b.quantity for b in db.scalars(select(Batch)).all())==100

def test_reserved_stock_excluded(client,headers,db):
    b=add_batch(client,headers).json();batch=db.get(Batch,b['id']);batch.reserved=75;db.commit()
    assert client.get('/api/inventory/1',headers=headers()).json()['available']==25
    assert client.post('/api/inventory/stock-out',headers=headers(),json={'product_id':1,'warehouse_id':1,'quantity':26,'reference':'reserved test'}).status_code==409

def test_purchase_approval_and_audit(client,headers,db):
    r=client.post('/api/purchase-orders',headers=headers('operator'),json={'supplier_id':1,'items':[{'product_id':1,'quantity':20}]})
    assert r.status_code==201,r.text
    order=r.json();assert order['status']=='draft' and order['total']==400
    assert client.post(f'/api/purchase-orders/{order["id"]}/approve',headers=headers('operator'),json={'reason':'Approved by operator'}).status_code==403
    r=client.post(f'/api/purchase-orders/{order["id"]}/approve',headers=headers(),json={'reason':'Budget and quantity checked'})
    assert r.status_code==200 and r.json()['approved_by']=='admin'
    assert client.post(f'/api/purchase-orders/{order["id"]}/approve',headers=headers(),json={'reason':'Repeated approval'}).status_code==409
    assert db.scalar(select(AuditLog).where(AuditLog.action=='approved-purchase-order'))

def test_order_catalog_and_moq(client,headers):
    assert client.post('/api/purchase-orders',headers=headers(),json={'supplier_id':1,'items':[{'product_id':1,'quantity':2}]}).status_code==422

def test_excursion_quarantine_recovery_and_investigation(client,headers,db):
    b=add_batch(client,headers).json()
    db.add(TemperatureSensor(name='Test logger',warehouse_id=1,product_id=1));db.commit()
    from backend.app.models import now
    start=now()-timedelta(hours=1)
    for minutes,temp in [(0,5),(15,10),(30,11),(45,5)]:
        r=client.post('/api/cold-chain/readings',headers=headers(),json={'sensor_id':1,'timestamp':(start+timedelta(minutes=minutes)).isoformat(),'temperature':temp})
        assert r.status_code==201,r.text
    excursion=db.scalar(select(TemperatureExcursion));assert excursion.duration_minutes==30 and excursion.ended_at
    assert excursion.affected_batches==[b['id']]
    db.refresh(db.get(Batch,b['id']));assert db.get(Batch,b['id']).status=='quarantined'
    alert=db.scalar(select(ColdChainAlert))
    assert client.post(f'/api/cold-chain/alerts/{alert.id}/investigate',headers=headers('operator'),json={'reason':'Inspect logger'}).status_code==403
    assert client.post(f'/api/cold-chain/alerts/{alert.id}/investigate',headers=headers('quality'),json={'reason':'Quality procedure QA-001 initiated'}).status_code==200
    assert client.get('/api/inventory/1',headers=headers()).json()['available']==0

def test_sensor_validation_gaps_failure(client,headers,db):
    from backend.app.models import now
    db.add(TemperatureSensor(name='Test',warehouse_id=1,product_id=1));db.commit()
    start=now()-timedelta(hours=2)
    assert client.post('/api/cold-chain/readings',headers=headers(),json={'sensor_id':1,'timestamp':start.isoformat(),'temperature':5}).status_code==201
    assert client.post('/api/cold-chain/readings',headers=headers(),json={'sensor_id':1,'timestamp':start.isoformat(),'temperature':5}).status_code==409
    assert client.post('/api/cold-chain/readings',headers=headers(),json={'sensor_id':1,'timestamp':now().isoformat(),'temperature':5,'sensor_status':'failed'}).status_code==201
    alerts=db.scalars(select(ColdChainAlert)).all();assert len(alerts)==2

def test_formulas():
    assert safety_stock(10,4)==pytest.approx(32.9)
    assert reorder_point(20,4,33)==113
    assert eoq(10000,50,2)==pytest.approx(707.10678)
    with pytest.raises(ValueError):eoq(100,50,0)

def demand(db):
    for i in range(120):db.add(DemandHistory(product_id=1,day=date.today()-timedelta(days=120-i),quantity=20+i%7))
    db.commit()

def test_forecast_and_agent_pipeline(client,headers,db):
    demand(db);add_batch(client,headers)
    f=client.post('/api/forecast/run',headers=headers(),json={'product_id':1,'horizon':14})
    assert f.status_code==200,f.text
    result=f.json();assert len(result['forecast'])==14
    assert result['split']=={'train':72,'validation':24,'test':24}
    assert result['forecast'][0]['date']==str(date.today())
    r=client.post('/api/agents/run',headers=headers(),json={'product_id':1})
    assert r.status_code==200,r.text
    assert len(r.json()['outputs'])==10
    logs=db.scalars(select(AgentExecution)).all();assert len(logs)==10
    assert all(log.duration_ms>=0 and log.status=='completed' for log in logs),[(x.agent,x.error) for x in logs]
    rec=client.post('/api/rl/recommend',headers=headers(),json={'product_id':1}).json()
    assert rec['human_approval_required'] and 'baseline' in rec['source'].lower()

def test_exports_and_imports(client,headers):
    for fmt in ['csv','json','pdf']:
        r=client.get(f'/api/export/inventory?format={fmt}',headers=headers());assert r.status_code==200
        if fmt=='pdf':assert r.content.startswith(b'%PDF')
    r=client.post('/api/import/products',headers=headers(),json=[{'name':'Imported synthetic product'}]);assert r.status_code==200
    assert r.json()['created']==1

def test_policy_screening_retains_baseline(client,headers,db):
    from backend.app.models import RLTrainingRun,RLModel
    demand(db)
    run=RLTrainingRun(status='completed',config={'algorithm':'PPO'},result={'evaluation':{'results':[{'policy':'RL policy','service_level':.1,'total_cost':20000},{'policy':'EOQ','service_level':.99,'total_cost':800}]}})
    db.add(run);db.flush();db.add(RLModel(version='test-bad',path='no-checkpoint-needed.zip',algorithm='PPO',training_run_id=run.id));db.commit()
    result=client.post('/api/rl/recommend',headers=headers(),json={'product_id':1})
    assert result.status_code==200,result.text
    assert 'failed screening' in result.json()['source']
    assert result.json()['model_version'] is None and result.json()['candidate_version']=='test-bad'

def test_adjustment_preserves_quarantine_and_reserves(client,headers,db):
    b=add_batch(client,headers).json()
    result=client.post(f'/api/inventory/batches/{b["id"]}/adjust',headers=headers(),json={'quantity':100,'reserved':30,'reason':'Reserve for synthetic demand'})
    assert result.status_code==200 and result.json()['reserved']==30
    batch=db.get(Batch,b['id']);batch.status='quarantined';db.commit()
    assert client.post(f'/api/inventory/batches/{b["id"]}/adjust',headers=headers(),json={'quantity':0,'reserved':0,'reason':'Remove quarantined stock'}).status_code==409

def test_warehouse_sensor_catalog_configuration(client,headers):
    w=client.post('/api/warehouses',headers=headers(),json={'name':'New warehouse','region':'test','capacity':1000,'cold_capacity':500})
    assert w.status_code==201
    assert client.post('/api/cold-chain/sensors',headers=headers(),json={'name':'New logger','warehouse_id':w.json()['id'],'product_id':1}).status_code==201
    assert client.post('/api/cold-chain/sensors',headers=headers(),json={'name':'No location','product_id':1}).status_code==422
    assert client.post('/api/suppliers/1/catalog',headers=headers(),json={'product_id':1,'unit_cost':10}).status_code==409

def test_hosted_training_is_explicitly_disabled(client,headers,monkeypatch):
    monkeypatch.setenv('RL_TRAINING_ENABLED','false')
    response=client.post('/api/rl/train',headers=headers(),json={'algorithm':'PPO','timesteps':4096,'seed':42})
    assert response.status_code==503
    assert 'local workstation' in response.json()['detail']
