import time, uuid
from typing import TypedDict
from datetime import date
from sqlalchemy import select
from langgraph.graph import StateGraph, END
from .models import *
from .schemas import AgentOutput
from .inventory import summary
from .forecasting import run_forecast
from .optimization import recommendation
from .cold_chain import sensor_health

AGENTS = [
    ('inventory', 'Inventory monitoring', 'Usable stock, reserves and shortages'),
    ('forecast', 'Demand forecasting', 'Chronological forecast selection and evaluation'),
    ('rl', 'RL inventory optimization', 'Policy inference with hard inventory limits'),
    ('cold_chain', 'Cold-chain monitoring', 'Sensor health and product-specific excursions'),
    ('cold_risk', 'Cold-chain risk prediction', 'Statistical trend and anomaly screening'),
    ('expiry', 'Expiry & batch management', 'Remaining shelf life and FEFO allocation'),
    ('supplier', 'Supplier & replenishment', 'Lead time, cost and reliability'),
    ('risk', 'Integrated risk assessment', 'Consolidated evidence-backed risks'),
    ('recommendation', 'Decision support', 'Explainable actions requiring human approval'),
    ('orchestrator', 'Orchestrator', 'Validate and consolidate partial results'),
]

class WorkflowState(TypedDict):
    product_id: int
    run_id: str
    outputs: dict

def execute(db, product_id):
    def node(key):
        def run(state):
            start = time.perf_counter()
            status, error = 'completed', None
            try:
                with db.begin_nested():
                    output = compute(key, db, state)
                    output = AgentOutput.model_validate(output).model_dump()
            except Exception as exc:
                status, error = 'failed', f'{type(exc).__name__}: {str(exc)[:300]}'
                output = AgentOutput(summary='Agent failed; downstream agents receive partial results', evidence={}, warnings=[error]).model_dump()
            db.add(AgentExecution(run_id=state['run_id'], agent=key, status=status, duration_ms=(time.perf_counter()-start)*1000, input_summary={'product_id': product_id, 'upstream': list(state['outputs'])}, output=output, error=error))
            db.flush()
            return {'outputs': {**state['outputs'], key: output}}
        return run
    graph = StateGraph(WorkflowState)
    for key, _, _ in AGENTS:
        graph.add_node(key, node(key))
    graph.set_entry_point(AGENTS[0][0])
    for (a, _, _), (b, _, _) in zip(AGENTS, AGENTS[1:]): graph.add_edge(a, b)
    graph.add_edge('orchestrator', END)
    result = graph.compile().invoke({'product_id': product_id, 'run_id': str(uuid.uuid4()), 'outputs': {}})
    return result

def compute(key, db, state):
    pid = state['product_id']
    evidence, recommendations, warnings = {}, [], []
    if key == 'inventory':
        evidence = {'inventory': summary(db, pid)}
    elif key == 'forecast':
        evidence = run_forecast(db, pid)
    elif key == 'rl':
        evidence = recommendation(db, pid); recommendations = [evidence]
    elif key == 'cold_chain':
        evidence = {'sensors': sensor_health(db), 'excursions': [{'id': x.id, 'batch_ids': x.affected_batches, 'duration_minutes': x.duration_minutes} for x in db.scalars(select(TemperatureExcursion)).all()]}
    elif key == 'cold_risk':
        scores = []
        for sensor in db.scalars(select(TemperatureSensor)).all():
            rows = db.scalars(select(TemperatureReading).where(TemperatureReading.sensor_id == sensor.id).order_by(TemperatureReading.timestamp.desc()).limit(24)).all()
            if len(rows) < 5: continue
            import numpy as np
            y = np.array([r.temperature for r in reversed(rows)])
            baseline, std = y[:-1].mean(), max(.2, y[:-1].std())
            p = db.get(Product, sensor.product_id)
            z = abs(y[-1]-baseline)/std
            slope = float(np.polyfit(np.arange(len(y)), y, 1)[0])
            score = min(100, z*15+abs(slope)*50+(50 if not p.temp_min <= y[-1] <= p.temp_max else 0))
            scores.append({'sensor_id': sensor.id, 'risk_score': round(float(score), 1), 'z_score': float(z), 'trend_per_reading': slope, 'reading_ids': [r.id for r in rows], 'category': 'high' if score > 60 else 'moderate' if score > 30 else 'low'})
        evidence = {'statistical_screening': scores, 'method': 'Trailing-window z-score and linear trend; uncalibrated anomaly indicator'}
        warnings = ['Anomaly score does not determine product stability or suitability for use']
    elif key == 'expiry':
        rows = db.scalars(select(Batch).where(Batch.product_id == pid).order_by(Batch.expiry_date)).all()
        evidence = {'fefo': [{'batch_id': b.id, 'expiry': b.expiry_date.isoformat(), 'days_remaining': (b.expiry_date-date.today()).days, 'status': b.status} for b in rows]}
    elif key == 'supplier':
        evidence = recommendation(db, pid)
    elif key == 'risk':
        stock = summary(db, pid)[0]
        risks = []
        for condition, kind, source in [(stock['status'] == 'low', 'stockout', f'products/{pid}'), (stock['status'] == 'excess', 'overstock', f'products/{pid}'), (stock['near_expiry'] > 0, 'expiry', 'inventory/batches'), (stock['quarantined'] > 0, 'cold-chain/quality hold', 'cold-chain/excursions')]:
            if condition: risks.append({'type': kind, 'source': source, 'product_id': pid})
        evidence = {'risks': risks, 'inventory': stock}
        db.add(RiskAssessment(result=evidence))
    elif key == 'recommendation':
        evidence = {'sources': list(state['outputs'])}
        rec = state['outputs'].get('rl', {}).get('evidence', {})
        if rec: recommendations.append(rec)
        stock = summary(db, pid)[0]
        if stock['quarantined']:
            recommendations.append({'action': 'Investigate quarantined batches using approved quality procedures', 'supporting_data': {'quantity': stock['quarantined']}, 'expected_benefit': 'Preserve traceability and assess excursion', 'risks': ['Disposition requires authorized quality review'], 'uncertainty': 'No stability determination available', 'human_approval_required': True})
    else:
        evidence = {'run_id': state['run_id'], 'completed_nodes': list(state['outputs']), 'synthetic': True}
        warnings = [w for v in state['outputs'].values() for w in v.get('warnings', [])]
    return {'summary': dict((k, name) for k, name, _ in AGENTS)[key]+' completed from current database records', 'evidence': evidence, 'recommendations': recommendations, 'warnings': warnings}
