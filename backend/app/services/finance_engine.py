from typing import Dict, Any
import logging

logger = logging.getLogger("masaad-api")

class FinanceEngine:
    """
    Consolidated Financial Engine for Madinat Al Saada Group.
    Calculates the True Burdened Rate by merging group-wide admin expenses 
    with factory-specific labor costs.
    """
    def __init__(self, db_pool=None):
        self.db = db_pool

    def calculate_burdened_rate(self, factory_payroll: float, madinat_admin_total: float, factory_headcount: int) -> float:
        """
        True_Hourly_Rate = (Total_Factory_Payroll + Total_Madinat_Admin) / (Factory_Headcount * 208 hours)
        Treats 'MADINAT' admin column as the primary group overhead.
        """
        if factory_headcount == 0:
            logger.error("Factory headcount is zero. Cannot calculate rate.")
            return 0.0
            
        # 208 hours = 8 hours/day * 26 working days (UAE standard industrial month)
        total_burdened_cost = factory_payroll + madinat_admin_total
        true_hourly_rate = total_burdened_cost / (factory_headcount * 208)
        
        return round(true_hourly_rate, 2)

    def calculate_project_margin(self, direct_cost: float, profit_pct: float) -> float:
        """
        Applies target profit on top of the established burdened cost.
        """
        return round(direct_cost * (1 + (profit_pct / 100)), 2)
