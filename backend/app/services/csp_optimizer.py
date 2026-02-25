from ortools.sat.python import cp_model
from typing import List, Dict, Any

class CSPOptimizer:
    def __init__(self, stock_length: int = 6000, kerf: int = 4, end_trim: int = 50):
        self.stock_length = stock_length
        self.kerf = kerf
        self.usable_stock = stock_length - (end_trim * 2)

    def solve_1d_csp(self, demands: List[int], offcuts: List[Dict]) -> Dict[str, Any]:
        model = cp_model.CpModel()
        bins = [{"capacity": o['length'], "id": o['id']} for o in offcuts]
        for _ in range(len(demands)): bins.append({"capacity": self.usable_stock})
        num_items, num_bins = len(demands), len(bins)
        x = {(i, j): model.NewBoolVar(f'x_{i}_{j}') for i in range(num_items) for j in range(num_bins)}
        y = [model.NewBoolVar(f'y_{j}') for j in range(num_bins)]
        for i in range(num_items): model.Add(sum(x[i, j] for j in range(num_bins)) == 1)
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
                    if remnant > 1000: new_remnants.append(remnant)
            return {"plan": plan, "new_remnants": new_remnants, "total_bins": len(plan)}
        return {"error": "Solver failed"}