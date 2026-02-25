from typing import List, Dict, Any
import math

class NestingEngine2D:
    """
    Shelf-Packing Nesting Optimizer for ACP and Glass Sheets.
    """
    def __init__(self, stock_w: float = 1250.0, stock_h: float = 3200.0):
        self.stock_w = stock_w
        self.stock_h = stock_h

    def optimize_acp_sheets(self, cassettes: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Input: List of {'w': float, 'h': float} including returns.
        Goal: Minimize sheet count.
        """
        # Sort by height descending (FFDH heuristic)
        sorted_items = sorted(cassettes, key=lambda x: x['h'], reverse=True)
        
        sheets = []
        current_sheet = {"id": 1, "used_area": 0, "shelves": []}
        
        for item in sorted_items:
            packed = False
            # Check existing shelves
            for shelf in current_sheet["shelves"]:
                if item["h"] <= shelf["h"] and (shelf["used_w"] + item["w"]) <= self.stock_w:
                    shelf["used_w"] += item["w"]
                    current_sheet["used_area"] += item["w"] * item["h"]
                    packed = True
                    break
            
            if not packed:
                # Create new shelf
                last_y = current_sheet["shelves"][-1]["y"] + current_sheet["shelves"][-1]["h"] if current_sheet["shelves"] else 0
                if (last_y + item["h"]) <= self.stock_h:
                    current_sheet["shelves"].append({"y": last_y, "h": item["h"], "used_w": item["w"]})
                    current_sheet["used_area"] += item["w"] * item["h"]
                    packed = True
            
            if not packed:
                # New Sheet required
                sheets.append(current_sheet)
                current_sheet = {
                    "id": len(sheets) + 1,
                    "used_area": item["w"] * item["h"],
                    "shelves": [{"y": 0, "h": item["h"], "used_w": item["w"]}]
                }

        sheets.append(current_sheet)
        
        total_sheet_area = len(sheets) * self.stock_w * self.stock_h
        total_net_area = sum(s["used_area"] for s in sheets)
        yield_pct = (total_net_area / total_sheet_area) * 100

        return {
            "total_sheets": len(sheets),
            "total_purchased_sqm": total_sheet_area / 1e6,
            "net_geometric_sqm": total_net_area / 1e6,
            "material_yield_pct": round(yield_pct, 2)
        }
