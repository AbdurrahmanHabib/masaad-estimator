import ezdxf
from typing import Dict, List, Any, Optional
import asyncpg

class StructuralEngine:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.E = 70000 

    def calculate_required_inertia(self, wind_pressure_kpa: float, span_mm: float, spacing_mm: float) -> float:
        w = (wind_pressure_kpa / 1000) * spacing_mm 
        L = span_mm
        i_req = (5 * w * (L**3) * 175) / (384 * self.E)
        return i_req 

    async def find_safe_alternative(self, current_item_code: str, i_req: float) -> Optional[Dict]:
        query = "SELECT item_code, inertia_ixx, base_cost_aed FROM catalog_items WHERE category = 'Profile' AND inertia_ixx >= $1 AND item_code LIKE LEFT($2, 8) || '%' ORDER BY inertia_ixx ASC LIMIT 1"
        async with self.db.acquire() as conn:
            return await conn.fetchrow(query, i_req, current_item_code)

    def override_dxf_blocks(self, dxf_path: str, old_block_name: str, new_block_name: str):
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        if "AI_ENGINEERING_OVERRIDES" not in doc.layers:
            doc.layers.new(name="AI_ENGINEERING_OVERRIDES", dxfattr={'color': 1})
        count = 0
        for insert in msp.query(f'INSERT[name=="{old_block_name}"]'):
            insert.dxf.name = new_block_name
            insert.dxf.layer = "AI_ENGINEERING_OVERRIDES"
            count += 1
        doc.save()
        return count