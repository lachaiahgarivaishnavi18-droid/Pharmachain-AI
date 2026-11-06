"""Provider boundary: explanations never alter operational decisions."""
import os
from typing import Protocol
import httpx
from pydantic import BaseModel,Field

class Explanation(BaseModel):
    summary:str
    limitations:list[str]=Field(default_factory=list)
    provider:str='local'

class ExplanationProvider(Protocol):
    def explain(self,evidence:dict)->Explanation: ...

class LocalProvider:
    def explain(self,evidence):
        return Explanation(summary=f"{evidence.get('action','Review current evidence')}: {evidence.get('quantity',0)} units proposed. Available inventory is {evidence.get('available',0)} units; inventory position includes {evidence.get('pending',0)} pending units. The source is {evidence.get('source','deterministic tools')}. Human approval is required before a financial commitment.",limitations=evidence.get('risks',[]))

class RemoteProvider:
    """Optional JSON explanation gateway. Contract documented in docs/architecture.md."""
    def explain(self,evidence):
        endpoint=os.environ['LLM_EXPLANATION_URL']
        if not endpoint.startswith('https://'):raise ValueError('Remote explanation gateway must use HTTPS')
        headers={'Authorization':f"Bearer {os.environ['LLM_API_KEY']}"} if os.getenv('LLM_API_KEY') else {}
        response=httpx.post(endpoint,json={'task':'explain_only','evidence':evidence,'constraints':['Do not change quantities or authorize release, disposal, use or supplier spending']},headers=headers,timeout=20)
        response.raise_for_status()
        result=Explanation.model_validate(response.json());result.provider='remote gateway (advisory text only)';return result

def explain(evidence):
    if os.getenv('LLM_PROVIDER','local')=='remote':
        try:return RemoteProvider().explain(evidence).model_dump()
        except Exception:
            result=LocalProvider().explain(evidence);result.limitations.append('Remote explanation unavailable; deterministic fallback used');return result.model_dump()
    return LocalProvider().explain(evidence).model_dump()
