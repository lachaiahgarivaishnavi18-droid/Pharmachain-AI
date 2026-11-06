"""Portable deterministic inference for exported MLP policies, without PyTorch."""
import json
from pathlib import Path
import numpy as np

class NumpyPolicy:
    def __init__(self,path):
        self.config=json.loads(Path(path).read_text())
    def predict(self,observation,deterministic=True):
        x=np.asarray(observation,dtype=np.float32)
        for layer in self.config['layers']:
            x=x@np.asarray(layer['weight'],dtype=np.float32).T+np.asarray(layer['bias'],dtype=np.float32)
            if layer.get('activation')=='tanh':x=np.tanh(x)
            elif layer.get('activation')=='relu':x=np.maximum(0,x)
        if self.config['algorithm']=='PPO':return np.clip(x,0,1).astype(np.float32),None
        return np.asarray(np.argmax(x)),None

def load_policy(path,algorithm='PPO'):
    if str(path).endswith('.json'):return NumpyPolicy(path)
    from stable_baselines3 import PPO,DQN
    return (PPO if algorithm=='PPO' else DQN).load(path)
