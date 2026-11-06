import json,argparse
import numpy as np
from rl.environments.cold_chain_env import ColdChainEnv

def evaluate(path=None):
    model=None
    if path:
        from stable_baselines3 import PPO
        model=PPO.load(path)
    results=[]
    for policy in ['Threshold alerting','Statistical anomaly screening','Agentic rule-based response']+(['RL response'] if model else []):
        metrics=[]
        for seed in range(100,110):
            env=ColdChainEnv();obs,_=env.reset(seed=seed);history=[];missed=false=events=responses=cost=duration=0;delays=[];event_start=None;event_responded=False
            for step in range(env.horizon):
                outside=not env.lower<=env.temperature<=env.upper
                if outside and event_start is None:event_start=step;events+=1;event_responded=False
                if not outside:event_start=None;event_responded=False
                if policy=='Threshold alerting':action=2 if outside else 0
                elif policy=='Statistical anomaly screening':action=1 if len(history)>5 and abs(env.temperature-np.mean(history[-12:]))>max(.5,2*np.std(history[-12:])) else 0
                elif policy=='Agentic rule-based response':action=3 if outside else 5 if env.trend>.6 else 0
                else:action=int(model.predict(obs,deterministic=True)[0])
                alerted=action!=0
                missed+=int(outside and not alerted);false+=int(not outside and alerted);responses+=int(outside and alerted)
                if outside and alerted and event_start is not None and not event_responded:delays.append((step-event_start)*15);event_responded=True
                history.append(env.temperature);obs,_,_,_,info=env.step(action);cost+=info['response_cost'];duration+=15*int(info['outside'])
            metrics.append({'outside_steps_missed':missed,'false_alert_steps':false,'detected_response_steps':responses,'excursion_events':events,'mean_response_delay_minutes':float(np.mean(delays)) if delays else 0.,'simulated_excursion_minutes':duration,'operational_response_cost':cost})
        results.append({'policy':policy,**{k:float(np.mean([m[k] for m in metrics])) for k in metrics[0]}})
    return {'simulated':True,'seeds':list(range(100,110)),'results':results,'limitations':'15-minute steps; simplified action-dependent temperature response. Zero response delay with zero detections is not evidence of successful detection. Statistical screening detects deviations rather than stability. No product disposition actions.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--path');p.add_argument('--output',default='docs/cold-chain-evaluation.json');args=p.parse_args()
    result=evaluate(args.path);from pathlib import Path
    Path(args.output).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
