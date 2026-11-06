import math
import numpy as np
from sqlalchemy import select
from .models import *
from .inventory import require, summary

def safety_stock(std, lead_days, z=1.645):
    return z*std*math.sqrt(lead_days)

def reorder_point(mean, lead_days, safety):
    return mean*lead_days+safety

def eoq(annual_demand, ordering_cost, annual_holding_per_unit):
    if annual_holding_per_unit <= 0:
        raise ValueError('Annual holding cost must be positive')
    return math.sqrt(2*annual_demand*ordering_cost/annual_holding_per_unit)

def recommendation(db, product_id):
    p = require(db, Product, product_id)
    stock = summary(db, product_id)[0]
    history = db.scalars(select(DemandHistory.quantity).where(DemandHistory.product_id == product_id).order_by(DemandHistory.day.desc()).limit(30)).all()
    mean, std = float(np.mean(history)) if history else 0, float(np.std(history)) if history else 0
    mappings = db.scalars(select(SupplierProduct).where(SupplierProduct.product_id == product_id)).all()
    options = [{'supplier_id': m.supplier_id, 'unit_cost': m.unit_cost, 'minimum_order': m.minimum_order, 'lead_days': db.get(Supplier, m.supplier_id).lead_days, 'reliability': db.get(Supplier, m.supplier_id).reliability} for m in mappings]
    selected = min(options, key=lambda s: s['unit_cost']*(1+1-s['reliability'])) if options else None
    lead = selected['lead_days'] if selected else 7
    pending = db.execute(select(PurchaseOrderItem.quantity).join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.order_id).where(PurchaseOrderItem.product_id == product_id, PurchaseOrder.status.in_(['approved', 'in-transit']))).scalars().all()
    position = stock['available']+sum(pending)
    safety = safety_stock(std, lead)
    rop = reorder_point(mean, lead, safety)
    target = math.ceil(mean*(lead+14)+safety)
    quantity = max(0, min(p.max_stock-position, target-position)) if position < rop else 0
    source, model_version = 'Forecast-based baseline (no trained policy)', None
    model = db.scalar(select(RLModel).order_by(RLModel.id.desc()).limit(1))
    candidate_version = model.version if model else None
    policy_gate = 'No trained policy available'
    qualified = False
    if model:
        training = db.get(RLTrainingRun, model.training_run_id)
        evaluations = training.result.get('evaluation', {}).get('results', [])
        rl_metrics = next((e for e in evaluations if e['policy'] == 'RL policy'), None)
        baselines = [e for e in evaluations if e['policy'] != 'RL policy']
        qualified = bool(rl_metrics and baselines and rl_metrics['service_level'] >= .95 and rl_metrics['total_cost'] <= min(e['total_cost'] for e in baselines)*1.2)
        policy_gate = 'Simulation screening passed; operational validation still required' if qualified else 'Candidate failed simulation service/cost screening; forecast baseline retained'
        if not qualified:
            source = 'Forecast-based baseline (trained candidate failed screening)'
    if model and qualified:
        from rl.agents.policy import load_policy
        from rl.environments.pharmaceutical_inventory_env import PharmaceuticalInventoryEnv
        env = PharmaceuticalInventoryEnv(discrete=model.algorithm == 'DQN')
        env.reset(seed=42)
        env.batches = [[stock['available'], 60]]
        env.recent = [mean]*14
        env.pipeline = [(lead, q) for q in pending]
        policy = load_policy(model.path, model.algorithm)
        action, _ = policy.predict(env.observation(), deterministic=True)
        proposed = env.action_quantity(action)
        quantity = max(0, min(p.max_stock-position, proposed))
        source, model_version = 'RL policy, capped by inventory constraints', model.version
    if quantity and selected:
        quantity = max(quantity, selected['minimum_order'])
        quantity = min(quantity, max(0, p.max_stock-position))
        if quantity < selected['minimum_order']:
            quantity = 0
    result = {'product_id': product_id, 'product': p.name, 'action': 'Prepare replenishment draft' if quantity else 'Monitor inventory', 'quantity': int(quantity), 'source': source, 'model_version': model_version, 'candidate_version': candidate_version, 'policy_gate': policy_gate,
              'available': stock['available'], 'pending': sum(pending), 'inventory_position': position, 'mean_daily_demand': mean, 'demand_std': std, 'lead_days': lead,
              'safety_stock': round(safety, 2), 'reorder_point': round(rop, 2), 'eoq': round(eoq(mean*365, 500, max(p.unit_cost*.2, .01)), 2),
              'supplier': selected, 'supplier_comparison': options, 'estimated_cost': round(quantity*(selected['unit_cost'] if selected else p.unit_cost), 2),
              'expected_benefit': 'Increase coverage of lead-time demand', 'risks': ['Demand and lead times may differ from simulation', 'Warehouse cold capacity must be verified at receipt'],
              'uncertainty': 'Research demonstration; no calibrated operational confidence', 'human_approval_required': True}
    from .explanations import explain
    result['explanation'] = explain(result)
    db.add(RLRecommendation(product_id=product_id, result=result))
    return result
