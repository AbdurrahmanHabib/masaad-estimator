from ortools.linear_solver import pywraplp
from typing import List, Dict, Any
import math

class OptimizationEngine:
    """
    1D/2D Nesting for Madinat Al Saada Factory.
    Minimizes aluminum and sheet scrap.
    """
    def __init__(self, kerf_mm: float = 5.0, acp_return_mm: float = 50.0):
        self.kerf = kerf_mm
        self.acp_return = acp_return_mm

    def solve_1d_aluminum(self, demands: List[float], stock_length: float = 6000.0) -> Dict[str, Any]:
        """OR-Tools Bin Packing for extrusions."""
        solver = pywraplp.Solver.CreateSolver('SCIP')
        num_items = len(demands)
        num_bins = num_items # Worst case

        x = {}
        for i in range(num_items):
            for j in range(num_bins):
                x[i, j] = solver.IntVar(0, 1, f'x_{i}_{j}')
        y = [solver.IntVar(0, 1, f'y_{j}') for j in range(num_bins)]

        for i in range(num_items):
            solver.Add(sum(x[i, j] for j in range(num_bins)) == 1)
        for j in range(num_bins):
            solver.Add(sum(x[i, j] * (demands[i] + self.kerf) for i in range(num_items)) <= stock_length * y[j])

        solver.Minimize(sum(y[j] for j in range(num_bins)))
        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL:
            return {"total_bars": sum(int(y[j].solution_value()) for j in range(num_bins))}
        return {"error": "Optimization Failed"}

    def solve_2d_acp(self, panels: List[Dict[str, float]], sheet_dim: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculates sheet count with 50mm folding return allowance.
        """
        # Add 50mm to ALL 4 SIDES (+100mm to W and H)
        total_used_area = 0
        for p in panels:
            effective_w = p['w'] + (2 * self.acp_return)
            effective_h = p['h'] + (2 * self.acp_return)
            total_used_area += (effective_w * effective_h)
            
        sheet_area = sheet_dim['w'] * sheet_dim['h']
        # Conservative FFDH estimate for sheets
        required_sheets = math.ceil((total_used_area / sheet_area) * 1.15) # 15% safety for geometry
        
        return {
            "total_sheets": required_sheets,
            "net_area_sqm": round(total_used_area / 1e6, 2),
            "waste_pct": round((1 - (total_used_area / (required_sheets * sheet_area))) * 100, 2)
        }
