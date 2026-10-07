from decimal import Decimal
from app.config import settings

class CostEngine:
    @staticmethod
    def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
        rates = settings.MODEL_RATES.get(model_name, {"input": 2.50, "output": 10.00})
        
        input_rate = Decimal(str(rates["input"]))
        output_rate = Decimal(str(rates["output"]))
        
        prompt_cost = (Decimal(prompt_tokens) / Decimal(1_000_000)) * input_rate
        completion_cost = (Decimal(completion_tokens) / Decimal(1_000_000)) * output_rate
        
        return (prompt_cost + completion_cost).quantize(Decimal("0.000001"))

cost_engine = CostEngine()