from app.services.engineering_engine import StructuralEngine
from app.services.csp_optimizer import CSPOptimizer

async def structural_check_node(state: Dict):
    return {"detailed_bom": state.get("detailed_bom", []), "cost_variances": []}

async def csp_optimization_node(state: Dict):
    return {"cutting_plan": [], "stock_bars_to_order": 0}