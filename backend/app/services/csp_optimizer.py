try:
    from ortools.sat.python import cp_model as _cp_model
    _ORTOOLS_AVAILABLE = True
except ImportError:
    _cp_model = None
    _ORTOOLS_AVAILABLE = False

from typing import List, Dict, Any


def _greedy_1d_csp(demands: List[int], bins: List[Dict], kerf: int) -> Dict[str, Any]:
    """Fallback greedy first-fit-decreasing bin packer when ortools is unavailable."""
    sorted_demands = sorted(enumerate(demands), key=lambda x: -x[1])
    bin_remaining = [b["capacity"] for b in bins]
    bin_assignments: List[List[int]] = [[] for _ in bins]

    for orig_idx, demand in sorted_demands:
        placed = False
        for j, remaining in enumerate(bin_remaining):
            needed = demand + kerf
            if remaining >= needed:
                bin_remaining[j] -= needed
                bin_assignments[j].append(demand)
                placed = True
                break
        if not placed:
            # Open a new bin (use usable_stock — assume last element of bins is template)
            cap = bins[-1]["capacity"] if bins else 6000
            bin_remaining.append(cap - (demand + kerf))
            bin_assignments.append([demand])

    plan = []
    new_remnants = []
    for j, items in enumerate(bin_assignments):
        if not items:
            continue
        cap = bins[j]["capacity"] if j < len(bins) else bins[-1]["capacity"]
        remnant = cap - (sum(items) + len(items) * kerf)
        plan.append({"items": items, "remnant": remnant})
        if remnant > 1000:
            new_remnants.append(remnant)

    return {"plan": plan, "new_remnants": new_remnants, "total_bins": len(plan)}


class CSPOptimizer:
    def __init__(self, stock_length: int = 6000, kerf: int = 4, end_trim: int = 50):
        self.stock_length = stock_length
        self.kerf = kerf
        self.usable_stock = stock_length - (end_trim * 2)

    def solve_1d_csp(self, demands: List[int], offcuts: List[Dict]) -> Dict[str, Any]:
        bins = [{"capacity": o['length'], "id": o['id']} for o in offcuts]
        for _ in range(len(demands)):
            bins.append({"capacity": self.usable_stock})

        if not _ORTOOLS_AVAILABLE:
            return _greedy_1d_csp(demands, bins, self.kerf)

        cp_model = _cp_model
        num_items, num_bins = len(demands), len(bins)
        model = cp_model.CpModel()
        x = {(i, j): model.NewBoolVar(f'x_{i}_{j}') for i in range(num_items) for j in range(num_bins)}
        y = [model.NewBoolVar(f'y_{j}') for j in range(num_bins)]
        for i in range(num_items):
            model.Add(sum(x[i, j] for j in range(num_bins)) == 1)
        for j in range(num_bins):
            item_usage = sum(x[i, j] * (demands[i] + self.kerf) for i in range(num_items))
            model.Add(item_usage <= bins[j]["capacity"] * y[j])
        model.Minimize(sum(y[j] for j in range(num_bins)))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0
        if solver.Solve(model) in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            plan = []
            new_remnants = []
            for j in range(num_bins):
                if solver.Value(y[j]):
                    items = [demands[i] for i in range(num_items) if solver.Value(x[i, j])]
                    remnant = bins[j]["capacity"] - (sum(items) + len(items) * self.kerf)
                    plan.append({"items": items, "remnant": remnant})
                    if remnant > 1000:
                        new_remnants.append(remnant)
            return {"plan": plan, "new_remnants": new_remnants, "total_bins": len(plan)}
        return {"error": "Solver failed"}
