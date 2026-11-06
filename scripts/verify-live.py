"""Exercise the integrated synthetic workflow against a running local backend."""
import os,json,uuid
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
import httpx

client=httpx.Client(base_url='http://127.0.0.1:8000',timeout=180)
def call(method,path,**kwargs):
    response=client.request(method,path,**kwargs);response.raise_for_status();return response.json()
auth=call('POST','/api/auth/login',json={'username':'admin','password':os.environ['DEMO_PASSWORD']})
client.headers['Authorization']='Bearer '+auth['access_token']
suffix=uuid.uuid4().hex[:6]
product=call('POST','/api/products',json={'name':f'Synthetic workflow validation {suffix}','temperature_sensitive':True,'temp_min':2,'temp_max':8,'criticality':'critical'})
pid=product['id']
batch=call('POST','/api/inventory/stock-in',json={'number':f'E2E-{suffix}','product_id':pid,'warehouse_id':1,'quantity':60,'manufacturing_date':str(date.today()-timedelta(days=30)),'expiry_date':str(date.today()+timedelta(days=180))})
call('POST','/api/import/demand',json=[{'product_id':pid,'day':str(date.today()-timedelta(days=120-i)),'quantity':20+i%7} for i in range(120)])
forecast=call('POST','/api/forecast/run',json={'product_id':pid,'horizon':14})
recommendation=call('POST','/api/rl/recommend',json={'product_id':pid})
sensor=call('POST','/api/cold-chain/sensors',json={'name':f'E2E logger {suffix}','warehouse_id':1,'product_id':pid})
start=datetime.now(timezone.utc)-timedelta(minutes=30)
for i,temp in enumerate([5,10,5]):call('POST','/api/cold-chain/readings',json={'sensor_id':sensor['id'],'timestamp':(start+timedelta(minutes=10*i)).isoformat(),'temperature':temp,'source':'synthetic'})
stock=call('GET',f'/api/inventory/{pid}')
assert stock['available']==0 and stock['quarantined']==60
alerts=call('GET','/api/cold-chain/alerts');alert=next(a for a in alerts if a['sensor_id']==sensor['id'])
call('POST',f'/api/cold-chain/alerts/{alert["id"]}/investigate',json={'reason':'Synthetic integration test: quality investigation opened; no disposition authorized'})
call('POST','/api/suppliers/1/catalog',json={'product_id':pid,'unit_cost':10,'minimum_order':50})
order=call('POST','/api/purchase-orders',json={'supplier_id':1,'items':[{'product_id':pid,'quantity':100}]})
assert order['status']=='draft'
approved=call('POST',f'/api/purchase-orders/{order["id"]}/approve',json={'reason':'Synthetic integration test approval only; no supplier transmission'})
workflow=call('POST','/api/agents/run',json={'product_id':pid})
logs=call('GET','/api/agents/executions',params={'run_id':workflow['run_id']})
assert len(logs)==10 and all(x['status']=='completed' for x in logs),logs
report=client.get('/api/export/inventory?format=pdf');report.raise_for_status();assert report.content.startswith(b'%PDF')
out=Path('data/exports');out.mkdir(parents=True,exist_ok=True);(out/'integrated-report.pdf').write_bytes(report.content)
training=call('GET','/api/rl/training-history')
summary={'synthetic':True,'product_id':pid,'batch_id':batch['id'],'forecast_model':forecast['model'],'recommendation_source':recommendation['source'],'quarantine_after_recovery':stock['quarantined'],'purchase_order_status':approved['status'],'workflow_run_id':workflow['run_id'],'completed_agents':len(logs),'training_runs':[{'id':r['id'],'status':r['status']} for r in training],'report_generated':True}
Path('docs/live-verification.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
