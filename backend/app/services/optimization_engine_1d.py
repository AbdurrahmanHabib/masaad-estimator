from ortools.linear_solver import pywraplp
from typing import List, Dict, Any

class AluminumStockOptimizer:
    """
    1D Bin Packing Optimizer for Aluminum Profiles.
    """
    def __init__(self, kerf_mm: float = 5.0):
        self.kerf = kerf_mm

    def solve_1d_csp(self, demands: List[float], stock_length: float = 6000.0) -> Dict[str, Any]:
        """
        Groups mullions/transoms into minimum number of stock bars.
        """
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            return {"error": "Solver unavailable"}

        num_items = len(demands)
        # Max theoretical bins is number of items
        num_bins = num_items

        # x[i, j] = 1 if item i is in bin j
        x = {}
        for i in range(num_items):
            for j in range(num_bins):
                x[i, j] = solver.IntVar(0, 1, f'x_{i}_{j}')

        # y[j] = 1 if bin j is used
        y = {}
        for j in range(num_bins):
            y[j] = solver.IntVar(0, 1, f'y_{j}')

        # Each item must be in exactly one bin
        for i in range(num_items):
            solver.Add(sum(x[i, j] for j in range(num_bins)) == 1)

        # The amount in each bin must not exceed its capacity
        for j in range(num_bins):
            solver.Add(
                sum(x[i, j] * (demands[i] + self.kerf) for i in range(num_items))
                <= stock_length * y[j]
            )

        # Minimize the number of bins used
        solver.Minimize(sum(y[j] for j in range(num_bins)))

        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL:
            bins_used = []
            for j in range(num_bins):
                if y[j].solution_value() > 0.5:
                    items = [demands[i] for i in range(num_items) if x[i, j].solution_value() > 0.5]
                    waste = stock_length - (sum(items) + len(items) * self.kerf)
                    bins_used.append({"bar_id": j+1, "items": items, "waste_mm": round(waste, 2)})
            
            total_req = sum(demands)
            total_purchased = len(bins_used) * stock_length
            waste_pct = ((total_purchased - total_req) / total_purchased) * 100
            
            return {
                "total_bars": len(bins_used),
                "waste_percentage": round(waste_pct, 2),
                "cutting_list": bins_used
            }
        
        return {"error": "No optimal solution found"}
