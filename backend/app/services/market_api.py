import httpx
import logging
from typing import Dict, Any
from datetime import datetime
import asyncpg

class MarketDataService:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def get_market_rates(self) -> Dict[str, Any]:
        """Fetches live global rates (LME, FX)."""
        try:
            # Placeholder for Fastmarkets API
            return {"lme_alum_usd_mt": 2450.00, "eur_aed": 4.02, "usd_aed": 3.6725, "timestamp": datetime.utcnow()}
        except Exception as e:
            return {"lme_alum_usd_mt": 2400.0, "eur_aed": 4.0, "usd_aed": 3.6725, "timestamp": datetime.utcnow()}
            
    def calculate_uae_true_cost(
        self, 
        lme_usd_mt: float, 
        billet_premium_usd: float, 
        extrusion_cost_aed: float, 
        finish_type: str = "Standard Powder Coating", 
        is_thermal_break: bool = False
    ) -> float:
        """
        The Omniscient UAE Pricing Matrix.
        Formula: Total_AED = ((LME + Billet) * FX) / 1000 + Extrusion_Margin + Finish_Cost + Thermal_Break_Roll
        """
        # Convert MT to KG and USD to AED
        base_aed_per_kg = ((lme_usd_mt + billet_premium_usd) * 3.6725) / 1000
        
        # Apply standard UAE Finish Premiums
        finishing_cost_aed = 3.0 # Standard
        if finish_type.upper() == 'PVDF':
            finishing_cost_aed = 5.0
        elif finish_type.upper() == 'WOOD':
            finishing_cost_aed = 8.0
            
        # Polyamide rolling/insertion costs
        thermal_break_cost = 2.5 if is_thermal_break else 0.0 
        
        total_aed_per_kg = base_aed_per_kg + extrusion_cost_aed + finishing_cost_aed + thermal_break_cost
        return round(total_aed_per_kg, 2)