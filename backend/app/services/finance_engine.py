import pandas as pd
import io
from typing import Dict, Any, List

class FinanceEngine:
    """
    Unified Group Financial Engine.
    Consolidates Madinat Al Saada, Al Jazeera, and Madinat Al Jazeera.
    """
    def calculate_unified_group_rate(self, admin_csv_content: str, payroll_csv_list: List[str]) -> Dict[str, Any]:
        # 1. Total Group Overhead (Merge all three columns)
        admin_df = pd.read_csv(io.StringIO(admin_csv_content))
        admin_df.columns = admin_df.columns.str.strip().str.upper()
        
        target_cols = ['MADINAT', 'AL JAZEERA', 'MADINAT AL JAZEERA']
        # Sum every numeric value across the three shell entity columns
        valid_cols = [c for c in target_cols if c in admin_df.columns]
        total_group_overhead = admin_df[valid_cols].apply(pd.to_numeric, errors='coerce').sum().sum()

        # 2. Unified Labor Pool (Merge multiple payroll files)
        combined_payroll = pd.concat([pd.read_csv(io.StringIO(c)) for c in payroll_csv_list])
        combined_payroll.columns = combined_payroll.columns.str.strip().str.upper()

        # 3. Factory Filter & Active Hours
        factory_pool = combined_payroll[combined_payroll['SITE'].str.upper() == 'FACTORY']
        group_labor_cost = factory_pool['TOTAL SALARY'].sum()
        # 208 hours = 8 hours/day * 26 days
        active_factory_hours = len(factory_pool) * 208 

        # 4. The Unified SaaS Formula
        if active_factory_hours == 0: return {"error": "ZERO_FACTORY_HOURS"}
        
        true_shop_rate = (group_labor_cost + total_group_overhead) / active_factory_hours

        return {
            "group_overhead_total": round(total_group_overhead, 2),
            "factory_labor_total": round(group_labor_cost, 2),
            "factory_headcount": len(factory_pool),
            "true_shop_rate_aed": round(true_shop_rate, 2),
            "currency": "AED"
        }
