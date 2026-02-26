try:
    from ortools.linear_solver import pywraplp as _pywraplp
    _ORTOOLS_AVAILABLE = True
except ImportError:
    _pywraplp = None
    _ORTOOLS_AVAILABLE = False

from typing import List, Dict, Any
import math


def _greedy_1d_aluminum(demands: List[float], stock_length: float, kerf: float) -> Dict[str, Any]:
    """Fallback greedy first-fit-decreasing for aluminum profiles when ortools unavailable."""
    sorted_demands = sorted(demands, reverse=True)
    bars: List[float] = []  # remaining capacity per bar
    for d in sorted_demands:
        needed = d + kerf
        placed = False
        for i, rem in enumerate(bars):
            if rem >= needed:
                bars[i] -= needed
                placed = True
                break
        if not placed:
            bars.append(stock_length - needed)
    total_bars = len(bars)
    waste_pct = (1 - (sum(demands) / (total_bars * stock_length))) * 100 if total_bars else 0
    return {"total_bars": total_bars, "waste_pct": round(waste_pct, 2)}


class OptimizationEngine:
    """
    Industrial Nesting Engine.
    Minimizes scrap for Aluminum profiles and ACP sheets.
    """
    def __init__(self, kerf_mm: float = 5.0, acp_return_mm: float = 50.0):
        self.kerf = kerf_mm
        self.acp_return = acp_return_mm

    def solve_1d_aluminum(self, demands: List[float], stock_length: float = 6000.0) -> Dict[str, Any]:
        """OR-Tools (with greedy fallback) to find minimum 6m bars required."""
        if not _ORTOOLS_AVAILABLE:
            return _greedy_1d_aluminum(demands, stock_length, self.kerf)

        pywraplp = _pywraplp
        solver = pywraplp.Solver.CreateSolver('SCIP')
        num_items = len(demands)
        num_bins = num_items  # Upper bound

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
            total_bars = sum(int(y[j].solution_value()) for j in range(num_bins))
            waste_pct = (1 - (sum(demands) / (total_bars * stock_length))) * 100
            return {"total_bars": total_bars, "waste_pct": round(waste_pct, 2)}
        return {"error": "1D_OPTIMIZATION_FAILED"}

    def solve_2d_acp(self, panels: List[Dict[str, float]], sheet_dim: Dict[str, float]) -> Dict[str, Any]:
        """
        2D Bin Packing for ACP with mandatory 50mm fold depth return on all sides.
        """
        sheet_area = sheet_dim['w'] * sheet_dim['h']
        total_used_area = 0

        for p in panels:
            # Add 50mm to all 4 sides (+100mm total to each dimension)
            effective_w = p['w'] + (2 * self.acp_return)
            effective_h = p['h'] + (2 * self.acp_return)
            total_used_area += (effective_w * effective_h)

        # Simplified nesting efficiency factor (Heuristic)
        efficiency_factor = 1.12  # 12% extra for layout complexity
        required_sheets = math.ceil((total_used_area / sheet_area) * efficiency_factor)

        return {
            "total_sheets": required_sheets,
            "waste_pct": round((1 - (total_used_area / (required_sheets * sheet_area))) * 100, 2)
        }
