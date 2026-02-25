from simpleeval import SimpleEval
from typing import Dict, Any, List
import asyncpg

class BOMEngine:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.evaluator = SimpleEval()
    
    def _prepare_variables(self, dimensions: Dict[str, float]) -> Dict[str, float]:
        w, h = dimensions.get("width", 0), dimensions.get("height", 0)
        area = (w * h) / 1e6
        glass_density = dimensions.get("density", 15.0) 
        return {
            "w": w / 1000, "h": h / 1000, "area": area,
            "perimeter": (2 * (w + h)) / 1000, "weight": area * glass_density
        }

    async def explode_system(self, system_id: str, dimensions: Dict[str, float]) -> List[Dict[str, Any]]:
        async with self.db.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM explode_bom($1::uuid)", system_id)
        variables = self._prepare_variables(dimensions)
        self.evaluator.names = variables
        detailed_bom = []
        for row in rows:
            logic = row['parametric_logic']
            qty_formula = logic.get("qty_formula", "1")
            condition = logic.get("condition", "True")
            try:
                if not self.evaluator.eval(condition): continue
                final_qty = self.evaluator.eval(qty_formula)
                detailed_bom.append({
                    "item_code": row['item_code'],
                    "unit": row['unit_of_measure'],
                    "quantity": round(float(final_qty), 4),
                    "unit_cost": float(row['base_cost_aed']),
                    "subtotal": round(float(final_qty) * float(row['base_cost_aed']), 2)
                })
            except Exception as e:
                detailed_bom.append({"item_code": row['item_code'], "error": str(e)})
        return detailed_bom