from typing import List, Dict, Any

class LaborEngine:
    """
    Consolidates disparate payroll data into a single Madinat Al Saada blended rate.
    Reverts all inter-company routing logic.
    """
    def calculate_blended_rates(self, payroll_entries: List[Dict[str, Any]]) -> Dict[str, float]:
        total_monthly_payroll = 0.0
        total_factory_workers = 0
        total_site_workers = 0
        
        for employee in payroll_entries:
            # Aggregate salary regardless of visa-sponsoring entity
            total_monthly_payroll += employee.get('basic_salary', 0) + employee.get('allowances', 0)
            
            if employee.get('department') == 'FACTORY':
                total_factory_workers += 1
            elif employee.get('department') == 'SITE':
                total_site_workers += 1

        # Calculate Blended Hourly Rates (Assumes 208 working hours/month)
        # Includes Madinat Al Saada standard burden (Visa, Insurance, Accommodation)
        avg_monthly_salary = total_monthly_payroll / (total_factory_workers + total_site_workers)
        uae_burden_factor = 1.35 # Fixed overhead for accommodation/visas
        
        blended_hourly_rate = (avg_monthly_salary * uae_burden_factor) / 208
        
        return {
            "entity": "Madinat Al Saada Aluminium & Glass Works LLC",
            "total_unified_workforce": total_factory_workers + total_site_workers,
            "blended_factory_rate_aed": round(blended_hourly_rate, 2),
            "blended_site_rate_aed": round(blended_hourly_rate * 1.15, 2), # Site risk premium
            "currency": "AED"
        }