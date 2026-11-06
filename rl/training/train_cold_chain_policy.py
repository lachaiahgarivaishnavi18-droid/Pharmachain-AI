import argparse,json
from pathlib import Path
from stable_baselines3 import PPO
from rl.environments.cold_chain_env import ColdChainEnv

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--timesteps',type=int,default=4096);p.add_argument('--seed',type=int,default=42);p.add_argument('--path',default='rl/models/cold-chain');args=p.parse_args()
    model=PPO('MlpPolicy',ColdChainEnv(),seed=args.seed,n_steps=256,batch_size=64,device='cpu',verbose=0)
    model.learn(args.timesteps);Path(args.path).parent.mkdir(parents=True,exist_ok=True);model.save(args.path)
    print(json.dumps({'path':args.path+'.zip','timesteps':model.num_timesteps,'simulated':True,'operational_recommendations_only':True}))
