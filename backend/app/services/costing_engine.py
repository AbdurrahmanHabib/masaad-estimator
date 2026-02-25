from typing import List, Dict, Any

class CostingEngine:
    def __init__(self):
        self.billet_premium = 400.0
        self.extrusion_premium = 800.0
        self.powder_coating = 15.0
        self.factory_hourly_rate = 85.0
        self.overhead_pct = 0.12
        self.usd_aed = 3.6725

    def calculate_aluminum_material_cost(self, total_weight_kg: float, lme_usd_mt: float) -> float:
        rate = ((lme_usd_mt + self.billet_premium + self.extrusion_premium) / 1000 * self.usd_aed) + self.powder_coating
        return round(total_weight_kg * rate, 2)

    def calculate_labor_cost(self, bom: List[Dict], total_cuts: int) -> float:
        fab_cost = (total_cuts * 3 / 60) * self.factory_hourly_rate
        total_inst_cost = sum(item.get("quantity", 0) * 120 * (1.5 if (item.get("quantity", 0) * item.get("density_kg_m2", 25) > 100) else 1) for item in bom if item.get("category") == "Glass")
        return round(fab_cost + total_inst_cost, 2)

    def apply_margins(self, direct_cost: float, margin_pct: float) -> float:
        return round(direct_cost * (1 + self.overhead_pct) * (1 + margin_pct), 2)