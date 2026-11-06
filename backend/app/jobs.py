from pathlib import Path
from sqlalchemy import select
from .database import SessionLocal
from .models import RLTrainingRun, RLModel, RLPolicyEvaluation

ROOT = Path(__file__).resolve().parents[2]

def training_job(run_id):
    with SessionLocal() as db:
        run = db.get(RLTrainingRun, run_id)
        run.status = 'running'; db.commit()
        try:
            from rl.training.train_inventory_policy import train
            from rl.evaluation.compare_baselines import evaluate
            version = f'{run.config["algorithm"].lower()}-{run_id}'
            result = train(**run.config, path=str(ROOT/'rl'/'models'/version))
            result['evaluation'] = evaluate(result['path'], run.config['algorithm'])
            run.result, run.status = result, 'completed'
            db.add(RLModel(version=version, path=result['path'], algorithm=run.config['algorithm'], training_run_id=run.id))
            db.add(RLPolicyEvaluation(result=result['evaluation']))
            db.commit()
        except Exception as exc:
            db.rollback(); run = db.get(RLTrainingRun, run_id)
            run.status, run.result = 'failed', {'error': f'{type(exc).__name__}: {exc}'}
            db.commit()
