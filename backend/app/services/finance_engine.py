import pandas as pd
import io
from typing import Dict, Any, List

class FinanceEngine:
    """
    Unified Group Financial Engine.
    Consolidates Madinat Al Saada, Al Jazeera, and Madinat Al Jazeera.
    """
    def calculate_unified_group_rate(self, admin_csv_content: str, payroll_csv_list: List[str]) -> Dict[str, Any]:
        # 1. Total Group Overhead
        admin_df = pd.read_csv(io.StringIO(admin_csv_content))
        admin_df.columns = admin_df.columns.str.strip().str.upper()
        
        target_cols = ['MADINAT', 'AL JAZEERA', 'MADINAT AL JAZEERA']
        # Filter for existing columns and sum everything
        valid_cols = [c for c in target_cols if c in admin_df.columns]
        total_group_overhead = admin_df[valid_cols].apply(pd.to_numeric, errors='coerce').sum().sum()

        # 2. Unified Labor Pool
        combined_payroll = pd.concat([pd.read_csv(io.StringIO(c)) for c in payroll_csv_list])
        combined_payroll.columns = combined_payroll.columns.str.strip().str.upper()

        # 3. Factory Filter
        factory_pool = combined_payroll[combined_payroll['SITE'].str.upper() == 'FACTORY']
        group_labor_cost = factory_pool['TOTAL SALARY'].sum()
        active_factory_hours = len(factory_pool) * 208 # 208 standard working hours

        # 4. Final Unified Formula
        if active_factory_hours == 0: return {"error": "ZERO_FACTORY_HOURS"}
        
        true_shop_rate = (group_labor_cost + total_group_overhead) / active_factory_hours

        return {
            "total_group_overhead": round(total_group_overhead, 2),
            "group_labor_cost": round(group_labor_cost, 2),
            "active_factory_hours": active_factory_hours,
            "true_shop_rate_aed": round(true_shop_rate, 2),
            "entity_breakdown": {
                "MADINAT": admin_df['MADINAT'].sum() if 'MADINAT' in admin_df.columns else 0,
                "AL_JAZEERA": admin_df['AL JAZEERA'].sum() if 'AL JAZEERA' in admin_df.columns else 0,
                "MAJ": admin_df['MADINAT AL JAZEERA'].sum() if 'MADINAT AL JAZEERA' in admin_df.columns else 0
            }
        }
