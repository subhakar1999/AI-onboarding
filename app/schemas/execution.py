from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Message(BaseModel):
    role: str
    content: str

class ExecuteRequest(BaseModel):
    messages: List[Message]
    stream: bool = False
    context_tags: Optional[Dict[str, Any]] = None

class ExecuteResponse(BaseModel):
    response: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    budget_exhausted: bool