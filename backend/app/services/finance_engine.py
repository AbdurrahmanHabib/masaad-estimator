from typing import Dict, Any
import logging

logger = logging.getLogger("masaad-api")

class FinanceEngine:
    """
    Dynamic Financial Engine.
    Calculates the 'True Burdened Rate' - the floor price for every hour of factory time.
    """
    def __init__(self, db_pool=None):
        self.db = db_pool

    def calculate_burdened_shop_rate(self, total_factory_payroll: float, total_madinat_admin: float, factory_headcount: int) -> float:
        """
        Logic: (Total_Factory_Payroll + Total_Madinat_Admin) / (Factory_Headcount * 208 hours).
        Ensures that project labor covers both worker salaries and office overhead.
        """
        if factory_headcount <= 0:
            return 0.0
            
        # 208 hours = 8 hours/day * 26 working days
        total_monthly_overhead = total_factory_payroll + total_madinat_admin
        burdened_rate = total_monthly_overhead / (factory_headcount * 208)
        
        return round(burdened_rate, 2)

    def calculate_material_landed_cost(self, tonnage: float, lme_usd: float, billet_premium_usd: float) -> float:
        """Calculates AED cost for raw aluminum supply."""
        usd_aed = 3.6725
        rate_per_mt_aed = (lme_usd + billet_premium_usd) * usd_aed
        return round(tonnage * rate_per_mt_aed, 2)
