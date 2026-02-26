try:
    from ortools.linear_solver import pywraplp as _pywraplp
    _ORTOOLS_AVAILABLE = True
except ImportError:
    _pywraplp = None
    _ORTOOLS_AVAILABLE = False

from typing import List, Dict, Any


def _greedy_1d_csp(demands: List[float], stock_length: float, kerf: float) -> Dict[str, Any]:
    """Fallback greedy first-fit-decreasing bin packer when ortools is unavailable."""
    sorted_demands = sorted(enumerate(demands), key=lambda x: -x[1])
    bars: List[float] = []  # remaining capacity per bar
    bar_contents: List[List[float]] = []

    for _orig_idx, demand in sorted_demands:
        needed = demand + kerf
        placed = False
        for i, rem in enumerate(bars):
            if rem >= needed:
                bars[i] -= needed
                bar_contents[i].append(demand)
                placed = True
                break
        if not placed:
            bars.append(stock_length - needed)
            bar_contents.append([demand])

    bins_used = []
    for j, items in enumerate(bar_contents):
        waste = stock_length - (sum(items) + len(items) * kerf)
        bins_used.append({"bar_id": j + 1, "items": items, "waste_mm": round(waste, 2)})

    total_req = sum(demands)
    total_purchased = len(bins_used) * stock_length
    waste_pct = ((total_purchased - total_req) / total_purchased) * 100 if total_purchased else 0

    return {
        "total_bars": len(bins_used),
        "waste_percentage": round(waste_pct, 2),
        "cutting_list": bins_used,
    }


class AluminumStockOptimizer:
    """
    1D Bin Packing Optimizer for Aluminum Profiles.
    Uses OR-Tools when available; falls back to greedy FFD otherwise.
    """
    def __init__(self, kerf_mm: float = 5.0):
        self.kerf = kerf_mm

    def solve_1d_csp(self, demands: List[float], stock_length: float = 6000.0) -> Dict[str, Any]:
        """
        Groups mullions/transoms into minimum number of stock bars.
        """
        if not _ORTOOLS_AVAILABLE:
            return _greedy_1d_csp(demands, stock_length, self.kerf)

        pywraplp = _pywraplp
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            return _greedy_1d_csp(demands, stock_length, self.kerf)

        num_items = len(demands)
        num_bins = num_items  # Max theoretical bins is number of items

        x = {}
        for i in range(num_items):
            for j in range(num_bins):
                x[i, j] = solver.IntVar(0, 1, f'x_{i}_{j}')

        y = {}
        for j in range(num_bins):
            y[j] = solver.IntVar(0, 1, f'y_{j}')

        for i in range(num_items):
            solver.Add(sum(x[i, j] for j in range(num_bins)) == 1)
        for j in range(num_bins):
            solver.Add(
                sum(x[i, j] * (demands[i] + self.kerf) for i in range(num_items))
                <= stock_length * y[j]
            )

        solver.Minimize(sum(y[j] for j in range(num_bins)))
        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL:
            bins_used = []
            for j in range(num_bins):
                if y[j].solution_value() > 0.5:
                    items = [demands[i] for i in range(num_items) if x[i, j].solution_value() > 0.5]
                    waste = stock_length - (sum(items) + len(items) * self.kerf)
                    bins_used.append({"bar_id": j + 1, "items": items, "waste_mm": round(waste, 2)})

            total_req = sum(demands)
            total_purchased = len(bins_used) * stock_length
            waste_pct = ((total_purchased - total_req) / total_purchased) * 100

            return {
                "total_bars": len(bins_used),
                "waste_percentage": round(waste_pct, 2),
                "cutting_list": bins_used
            }

        return _greedy_1d_csp(demands, stock_length, self.kerf)
