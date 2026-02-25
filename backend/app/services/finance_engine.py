from typing import Dict, Any
import logging

logger = logging.getLogger("masaad-api")

class FinanceEngine:
    """
    Direct Profit Protection Engine.
    Calculates the True Burdened Rate from dynamic operational data.
    """
    def __init__(self, db_pool=None):
        self.db = db_pool

    async def calculate_burdened_rate(self, total_factory_payroll: float, total_madinat_admin: float, factory_headcount: int) -> float:
        """
        True_Hourly_Rate = (Total_Factory_Payroll + Total_Madinat_Admin) / (Factory_Headcount * 208 Hours)
        """
        if factory_headcount == 0:
            return 0.0
            
        # 208 Hours = 8 hours/day * 26 days (Standard UAE labor month)
        total_monthly_entity_cost = total_factory_payroll + total_madinat_admin
        true_hourly_rate = total_monthly_entity_cost / (factory_headcount * 208)
        
        return round(true_hourly_rate, 2)

    def apply_margins(self, direct_cost: float, profit_pct: float) -> float:
        """
        Final Sell Price: Only applied AFTER all true burdened costs are established.
        """
        return round(direct_cost * (1 + (profit_pct / 100)), 2)
