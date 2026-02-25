from typing import Dict, Any
import logging

logger = logging.getLogger("masaad-api")

class FinanceEngine:
    """
    Dynamic Finance Engine linked to SaaS configuration.
    Calculates project-specific rates based on uploaded operational data.
    """
    def __init__(self, db_pool=None):
        self.db = db_pool

    async def calculate_burdened_rate(self, payroll_data: Dict[str, float], admin_expenses: float) -> float:
        """
        True_Hourly_Rate = (Monthly_Payroll + Monthly_Admin_Expenses) / (Headcount * 260 Hours)
        payroll_data: {"factory_payroll": float, "headcount": int}
        """
        factory_payroll = payroll_data.get("factory_payroll", 0.0)
        headcount = payroll_data.get("headcount", 0)
        
        if headcount == 0:
            return 0.0
            
        # 260 Hours assumes 10 hours/day * 26 days (standard UAE industrial month)
        total_monthly_burden = factory_payroll + admin_expenses
        true_hourly_rate = total_monthly_burden / (headcount * 260)
        
        return round(true_hourly_rate, 2)

    def calculate_material_tonnage_cost(self, weight_kg: float, lme_usd: float, billet_premium_usd: float) -> float:
        """Calculates landed material cost in AED."""
        usd_aed = 3.6725
        rate_per_kg = ((lme_usd + billet_premium_usd) * usd_aed) / 1000
        return round(weight_kg * rate_per_kg, 2)
