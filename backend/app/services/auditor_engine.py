from typing import Dict, Any

class AuditorEngine:
    def __init__(self):
        pass

    def apply_dynamic_overheads(
        self, 
        base_cost: float, 
        admin_pct: float, 
        factory_pct: float, 
        risk_pct: float, 
        profit_pct: float
    ) -> Dict[str, float]:
        """
        Calculates the true project sell price using dynamic Quarter-specific overhead profiles.
        """
        admin_cost = base_cost * (admin_pct / 100)
        factory_cost = base_cost * (factory_pct / 100)
        risk_cost = base_cost * (risk_pct / 100)
        
        total_cost = base_cost + admin_cost + factory_cost + risk_cost
        
        # Profit is applied to the Total Cost (including overheads)
        profit_margin = total_cost * (profit_pct / 100)
        
        sell_price = total_cost + profit_margin
        
        return {
            "base_cost": round(base_cost, 2),
            "admin_overhead": round(admin_cost, 2),
            "factory_overhead": round(factory_cost, 2),
            "risk_contingency": round(risk_cost, 2),
            "total_cost": round(total_cost, 2),
            "profit_margin": round(profit_margin, 2),
            "sell_price": round(sell_price, 2)
        }