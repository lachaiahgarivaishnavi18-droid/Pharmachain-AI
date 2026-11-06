"""Build a secret-free serverless deployment from reviewed application source."""
import gzip,json,shutil
from pathlib import Path
import numpy as np
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from stable_baselines3 import PPO
from backend.app.database import Base,SessionLocal
from backend.app.models import RLTrainingRun,RLModel,RLPolicyEvaluation
from backend.app.seed import seed

root=Path(__file__).resolve().parents[1]
out=root/'deploy'/'vercel';out.mkdir(parents=True,exist_ok=True)
for name in ['backend/app','rl']:
    source=root/name;destination=out/name
    # Copy only source; never caches, local DB files, environment files or checkpoints.
    for item in source.rglob('*.py'):
        if '__pycache__' in item.parts:continue
        target=out/item.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(item,target)
shutil.copytree(root/'frontend'/'dist',out/'public',dirs_exist_ok=True)
(out/'backend'/'__init__.py').touch()
models=out/'rl'/'models';models.mkdir(parents=True,exist_ok=True)
policy=PPO.load(root/'rl'/'models'/'ppo-1.zip',device='cpu')
layers=[]
import torch
for layer in policy.policy.mlp_extractor.policy_net:
    if isinstance(layer,torch.nn.Linear):layers.append({'weight':layer.weight.detach().numpy().tolist(),'bias':layer.bias.detach().numpy().tolist(),'activation':'tanh'})
action=policy.policy.action_net
layers.append({'weight':action.weight.detach().numpy().tolist(),'bias':action.bias.detach().numpy().tolist(),'activation':'linear'})
policy_path=models/'ppo-1.json';policy_path.write_text(json.dumps({'algorithm':'PPO','layers':layers,'provenance':'Deterministic actor exported from actual local ppo-1 checkpoint; 4096 steps; seed 42'}))
from rl.agents.policy import NumpyPolicy
portable=NumpyPolicy(policy_path)
from rl.environments.pharmaceutical_inventory_env import PharmaceuticalInventoryEnv
env=PharmaceuticalInventoryEnv();obs,_=env.reset(seed=105)
for _ in range(20):
    actual,_=policy.predict(obs,deterministic=True);exported,_=portable.predict(obs)
    np.testing.assert_allclose(actual,exported,rtol=1e-5,atol=1e-6)
    obs,*_=env.step(actual)

# A fresh synthetic seed avoids exporting user-edited operational data or local credentials.
engine=create_engine('sqlite://');Base.metadata.create_all(engine)
with Session(engine,expire_on_commit=False) as db:
    seed(db)
    with SessionLocal() as local:
        run=local.get(RLTrainingRun,1)
        if run and run.status=='completed':
            result={**run.result,'path':'rl/models/ppo-1.json','provenance':'Actual local training run; portable deterministic inference exported for Vercel'}
            db.add(RLTrainingRun(id=1,status='completed',config=run.config,result=result));db.flush()
            db.add(RLModel(version='ppo-1',path='rl/models/ppo-1.json',algorithm='PPO',training_run_id=1))
            db.add(RLPolicyEvaluation(result=result['evaluation']));db.commit()
    snapshot={table.name:jsonable_encoder([dict(row) for row in db.execute(select(table)).mappings().all()]) for table in Base.metadata.sorted_tables}
snapshot_path=out/'demo-snapshot.json.gz';snapshot_path.write_bytes(gzip.compress(json.dumps(snapshot).encode()))
requirements=['fastapi==0.162.0','sqlalchemy==2.1.8','pydantic==2.14.3','PyJWT==2.15.1','numpy==2.5.4','scikit-learn==1.9.1','statsmodels==0.15.0','langgraph==1.2.20','gymnasium==1.4.0','httpx==0.28.1','reportlab==4.5.1','psycopg[binary]==3.3.8']
(out/'requirements.txt').write_text('\n'.join(requirements)+'\n')
(out/'.python-version').write_text('3.12\n')
api=out/'api';api.mkdir(exist_ok=True);shutil.copy2(root/'deployment'/'vercel-entrypoint.py',api/'index.py')
shutil.copy2(root/'deployment'/'vercel.json',out/'vercel.json')
(out/'.vercelignore').write_text('.vercel\n.env*\n**/__pycache__\n')
print(json.dumps({'directory':str(out),'files':sum(1 for x in out.rglob('*') if x.is_file() and '.vercel' not in x.parts and not x.name.startswith('.env')),'snapshot_bytes':snapshot_path.stat().st_size,'portable_policy_parity_checks':20}))
