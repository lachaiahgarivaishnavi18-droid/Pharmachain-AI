import json
import numpy as np
from rl.agents.policy import NumpyPolicy

def test_portable_ppo_inference(tmp_path):
    path=tmp_path/'policy.json'
    path.write_text(json.dumps({'algorithm':'PPO','layers':[{'weight':[[2.,-1.]],'bias':[.5],'activation':'tanh'},{'weight':[[1.]],'bias':[.1],'activation':'linear'}]}))
    policy=NumpyPolicy(path)
    action,_=policy.predict(np.array([.5,.5],dtype=np.float32))
    np.testing.assert_allclose(action,[np.tanh(1.)+.1],rtol=1e-6)

def test_portable_dqn_inference(tmp_path):
    path=tmp_path/'policy.json'
    path.write_text(json.dumps({'algorithm':'DQN','layers':[{'weight':[[1.,0.],[0.,2.]],'bias':[0.,0.],'activation':'linear'}]}))
    assert NumpyPolicy(path).predict([1.,1.])[0]==1
