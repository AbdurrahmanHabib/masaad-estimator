from typing import Dict, Any
import logging

logger = logging.getLogger("masaad-api")

class FinanceEngine:
    """
    Dynamic Finance Engine linked to SaaS configuration.
    Fetches active rates from the database instead of hardcoding variables.
    """
    def __init__(self, db_pool):
        self.db = db_pool

    async def get_active_tenant_rates(self) -> Dict[str, float]:
        """
        Retrieves the dynamically uploaded rates from the database.
        Returns 0.00 if no data has been uploaded (Zero-Knowledge start).
        """
        try:
            # Query the tenant_settings table (assuming it exists and has id=1 for the tenant)
            # async with self.db.acquire() as conn:
            #     row = await conn.fetchrow("SELECT true_shop_rate, total_admin_expenses, lme_rate, billet_premium, stock_length FROM tenant_settings WHERE id = 1")
            
            # Mocking the DB fetch for now until schema is updated
            row = None 
            
            if not row:
                logger.warning("No tenant settings found in database. Defaulting to 0.00.")
                return {
                    "true_shop_rate_aed": 0.00,
                    "total_admin_expenses_aed": 0.00,
                    "lme_rate_usd": 0.00,
                    "billet_premium_usd": 0.00,
                    "stock_length_m": 6.0
                }
                
            return {
                "true_shop_rate_aed": float(row['true_shop_rate']),
                "total_admin_expenses_aed": float(row['total_admin_expenses']),
                "lme_rate_usd": float(row['lme_rate']),
                "billet_premium_usd": float(row['billet_premium']),
                "stock_length_m": float(row['stock_length'])
            }
        except Exception as e:
            logger.error(f"Failed to fetch tenant rates: {e}")
            # Fail safe to zero to prevent unauthorized profit calculations
            return {
                "true_shop_rate_aed": 0.00,
                "total_admin_expenses_aed": 0.00,
                "lme_rate_usd": 0.00,
                "billet_premium_usd": 0.00,
                "stock_length_m": 6.0
            }

    async def calculate_loaded_cost(self, direct_material_cost: float, direct_labor_hours: float) -> float:
        """
        Calculates the final cost using ONLY the dynamically uploaded data.
        """
        rates = await self.get_active_tenant_rates()
        
        labor_cost = direct_labor_hours * rates["true_shop_rate_aed"]
        
        # Simplified dynamic overhead application
        # If admin expenses are extremely high, this simplistic ratio would need
        # to be adjusted based on the company's expected annual turnover.
        # Here we apply a simplistic percentage logic or just sum it if it's a project-specific allocation.
        
        # For demonstration: We assume total_admin_expenses is a monthly pool and 
        # needs to be distributed across active projects. 
        # We will apply a strict "Zero Data = Zero Value" rule.
        
        total_loaded_cost = direct_material_cost + labor_cost
        
        # Apply LME based material adjustments (simplified)
        if rates["lme_rate_usd"] > 0:
             # Just an example of how the dynamic variable affects the final cost
             material_lme_factor = (rates["lme_rate_usd"] + rates["billet_premium_usd"]) * 3.6725 / 1000
             total_loaded_cost += (direct_material_cost * material_lme_factor * 0.01) # Example scaling
             
        return round(total_loaded_cost, 2)