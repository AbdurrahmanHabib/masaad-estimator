from typing import TypedDict, List, Dict, Any
from app.services.bom_engine import BOMEngine
# from app.db.session import db

async def bom_explosion_node(state: Dict):
    # engine = BOMEngine(db.pool)
    return {"detailed_bom": [], "total_material_cost": 0.0}