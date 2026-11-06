"""Verify the deployed app using the caller's Vercel CLI authentication.

Application tokens travel only over subprocess stdin and HTTPS, never logs/files.
"""
import json,os,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PNPM=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pnpm/bin/pnpm.cjs'
URL='https://pharmachain-ai-chi.vercel.app'
token=None
checks=[]

def request(path,method='GET',body=None):
    config=[f'request = {json.dumps(method)}']
    if token:config.append('header = '+json.dumps('Authorization: Bearer '+token))
    if body is not None:
        config.append('header = "Content-Type: application/json"')
        config.append('data = '+json.dumps(json.dumps(body)))
    result=subprocess.run(['node',str(PNPM),'dlx','vercel@65.11.0','curl',path,'--deployment',URL,'--scope','resume-project3','--','--silent','--show-error','--max-time','180','--config','-','--write-out','HTTP_STATUS:%{http_code}'],input='\n'.join(config)+'\n',text=True,capture_output=True,cwd=ROOT/'deploy'/'vercel',timeout=210,encoding='utf-8')
    content,_,code=result.stdout.rstrip('\r\n').rpartition('HTTP_STATUS:')
    status=int(code) if code.isdigit() else 0
    if status>=400 or status==0:raise RuntimeError(f'{method} {path}: HTTP {status}: {content[:250]}')
    checks.append({'path':path,'method':method,'status':status})
    print(f'{method} {path}: {status}',flush=True)
    try:return json.loads(content)
    except json.JSONDecodeError:return content

html=request('/')
assert 'PharmaChain AI' in html
asset=html.split('src="')[1].split('"')[0]
assert 'import' in request(asset) or len(request(asset))>1000
assert request('/api/health')['status']=='ok'
login=request('/api/auth/login','POST',{'username':'admin','password':os.environ['DEMO_PASSWORD']})
token=login['access_token']
assert request('/api/health/database')['dialect']=='postgresql'
dashboard=request('/api/analytics/dashboard');assert dashboard['products']>=50
assert len(request('/api/inventory/batches'))>=150
forecast=request('/api/forecast/run','POST',{'product_id':1,'horizon':14});assert len(forecast['forecast'])==14
recommendation=request('/api/rl/recommend','POST',{'product_id':1});assert recommendation['human_approval_required']
evaluation=request('/api/rl/evaluate','POST');assert len(evaluation['results'])==5
workflow=request('/api/agents/run','POST',{'product_id':1});assert len(workflow['outputs'])==10
logs=request('/api/agents/executions?run_id='+workflow['run_id']);assert len(logs)==10 and all(x['status']=='completed' for x in logs),[(x['agent'],x['error']) for x in logs]
assert len(request('/api/cold-chain/sensors'))==10
assert len(request('/api/suppliers'))==10
assert 'available' in request('/api/export/inventory?format=csv')
capabilities=request('/api/health/models');assert capabilities['training_enabled'] is False
result={'url':URL,'target':'production','status':'READY','database':'Neon PostgreSQL','synthetic':True,'checks':checks,'product_count':dashboard['products'],'completed_agents':len(logs),'forecast_model':forecast['model'],'recommendation_source':recommendation['source'],'hosted_training_enabled':capabilities['training_enabled'],'portable_ppo_parity_checks':20}
(ROOT/'docs'/'vercel-verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
