import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env
from rl.environments.pharmaceutical_inventory_env import PharmaceuticalInventoryEnv,reward_components
from rl.environments.cold_chain_env import ColdChainEnv

@pytest.mark.parametrize('discrete',[False,True])
def test_gym_contract(discrete):
    check_env(PharmaceuticalInventoryEnv(discrete=discrete),skip_render_check=True)

def test_reward_components():
    parts=reward_components(10,2,50,20,3,1)
    assert parts=={'fulfillment':20.,'stockout':-24.,'holding':-1.5,'ordering':-17.,'expiry':-12.,'constraint':-20.,'cold_risk':-.5}
    assert reward_components(1,0,0,0,0,0,{'fulfillment':5})['fulfillment']==5

def test_expiry_capacity_and_termination():
    e=PharmaceuticalInventoryEnv(horizon=3,capacity=210);e.reset(seed=42);e.batches=[[200,0]]
    _,_,done,_,info=e.step(np.array([1.],dtype=np.float32));assert info['expired']==200 and info['violations']>0
    assert info['ordered']==10
    for _ in range(2):_,_,done,_,_=e.step(np.array([0.],dtype=np.float32))
    assert done
    with pytest.raises(ValueError):e.step(np.array([2.],dtype=np.float32))

def test_deterministic_scenarios():
    a,b=PharmaceuticalInventoryEnv(),PharmaceuticalInventoryEnv();a.reset(seed=123);b.reset(seed=123)
    for _ in range(20):
        ra=a.step(np.array([.2],dtype=np.float32));rb=b.step(np.array([.2],dtype=np.float32));assert ra[1]==rb[1];np.testing.assert_equal(ra[0],rb[0])

def test_cold_chain_action_safety():
    env=ColdChainEnv();check_env(env,skip_render_check=True)
    assert not any(word in action for action in env.actions for word in ['release','discard','use product'])
    env.reset(seed=42);assert env.step(1)[4]['human_review_required']

def test_model_roundtrip(tmp_path):
    from stable_baselines3 import PPO
    env=PharmaceuticalInventoryEnv();model=PPO('MlpPolicy',env,n_steps=32,batch_size=16,seed=42,device='cpu');model.learn(64)
    path=tmp_path/'test';model.save(path);loaded=PPO.load(path)
    obs,_=env.reset(seed=9);a,_=model.predict(obs,deterministic=True);b,_=loaded.predict(obs,deterministic=True);np.testing.assert_equal(a,b)
