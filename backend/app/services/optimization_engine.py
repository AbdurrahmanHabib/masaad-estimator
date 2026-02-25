from ortools.sat.python import cp_model
from typing import List, Dict, Any

class OptimizationEngine:
    """
    1D Cutting Stock Optimizer for Madinat Al Saada Factory Floor.
    Calculates minimum 6m bars required and exact cut patterns.
    """
    def __init__(self, kerf_mm: float = 5.0):
        self.kerf = kerf_mm

    def solve_1d_csp(self, demands: List[float], stock_length: float = 6000.0) -> Dict[str, Any]:
        model = cp_model.CpModel()
        
        # Max theoretical bars (worst case: one bar per cut)
        num_items = len(demands)
        num_bars = num_items
        
        # Variables: x[i, j] = 1 if item i is cut from bar j
        x = {}
        for i in range(num_items):
            for j in range(num_bars):
                x[i, j] = model.NewBoolVar(f'x_{i}_{j}')
        
        # y[j] = 1 if bar j is used
        y = [model.NewBoolVar(f'y_{j}') for j in range(num_bars)]
        
        # Constraints: Each item must be cut exactly once
        for i in range(num_items):
            model.Add(sum(x[i, j] for j in range(num_bars)) == 1)
            
        # Constraints: Total length in each bar must not exceed capacity
        for j in range(num_bars):
            # Sum of (length + kerf) <= stock_length * y[j]
            # Note: We subtract one kerf at the end because the last cut doesn't waste material 
            # unless we count end-trims. For simplicity, we add kerf to all and check against stock.
            item_usage = sum(x[i, j] * (demands[i] + self.kerf) for i in range(num_items))
            model.Add(item_usage <= stock_length * y[j])
            
        # Objective: Minimize bars used
        model.Minimize(sum(y[j] for j in range(num_bars)))
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15.0
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            bars_used = []
            for j in range(num_bars):
                if solver.Value(y[j]):
                    items = [demands[i] for i in range(num_items) if solver.Value(x[i, j])]
                    total_len = sum(items) + (len(items) * self.kerf)
                    bars_used.append({
                        "bar_id": j + 1,
                        "cuts": items,
                        "waste_mm": round(stock_length - total_len, 2)
                    })
            
            total_req_meters = sum(demands) / 1000
            total_purchased_meters = (len(bars_used) * stock_length) / 1000
            scrap_pct = ((total_purchased_meters - total_req_meters) / total_purchased_meters) * 100
            
            return {
                "total_bars": len(bars_used),
                "total_linear_meters_req": round(total_req_meters, 2),
                "total_meters_purchased": round(total_purchased_meters, 2),
                "scrap_percentage": round(scrap_pct, 2),
                "cutting_list": bars_used
            }
        
        return {"error": "Optimization Solver Failed"}