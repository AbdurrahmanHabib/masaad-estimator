from typing import List, Dict, Any
import math

class ACPNestingEngine:
    """
    2D Nesting for ACP sheets using a Shelf-Packing (FFDH) heuristic.
    Adds 50mm padding to all sides for 'Cassette Folding'.
    """
    def __init__(self, folding_offset_mm: float = 50.0):
        self.offset = folding_offset_mm

    def solve_2d_nesting(self, panels: List[Dict[str, float]], sheet_dim: Dict[str, float]) -> Dict[str, Any]:
        """
        panels: [{"w": 1200, "h": 2400}]
        sheet_dim: {"w": 1500, "h": 4000}
        """
        # Apply 50mm folding offset to all 4 sides (add 100mm to each dimension)
        processed_panels = []
        for p in panels:
            processed_panels.append({
                "w": p["w"] + (2 * self.offset),
                "h": p["h"] + (2 * self.offset),
                "original_id": p.get("id", "unknown")
            })

        # Sort panels by height descending (FFDH heuristic)
        processed_panels.sort(key=lambda x: x["h"], reverse=True)

        sheets = []
        current_sheet = {"id": 1, "shelves": [], "used_area": 0}
        
        def pack():
            nonlocal current_sheet
            for panel in processed_panels:
                packed = False
                # Try to fit in existing sheets/shelves
                for sheet in sheets + [current_sheet]:
                    for shelf in sheet["shelves"]:
                        if panel["h"] <= shelf["h"] and (shelf["used_w"] + panel["w"]) <= sheet_dim["w"]:
                            panel["x"] = shelf["used_w"]
                            panel["y"] = shelf["y"]
                            shelf["panels"].append(panel)
                            shelf["used_w"] += panel["w"]
                            sheet["used_area"] += panel["w"] * panel["h"]
                            packed = True
                            break
                    if packed: break
                    
                    # Create new shelf in current sheet
                    last_shelf_y = sheet["shelves"][-1]["y"] + sheet["shelves"][-1]["h"] if sheet["shelves"] else 0
                    if (last_shelf_y + panel["h"]) <= sheet_dim["h"]:
                        new_shelf = {"y": last_shelf_y, "h": panel["h"], "used_w": panel["w"], "panels": [panel]}
                        panel["x"] = 0
                        panel["y"] = last_shelf_y
                        sheet["shelves"].append(new_shelf)
                        sheet["used_area"] += panel["w"] * panel["h"]
                        packed = True
                        break
                
                if not packed:
                    # Start new sheet
                    if current_sheet["shelves"]:
                        sheets.append(current_sheet)
                    current_sheet = {
                        "id": len(sheets) + 2, 
                        "shelves": [{"y": 0, "h": panel["h"], "used_w": panel["w"], "panels": [panel]}],
                        "used_area": panel["w"] * panel["h"]
                    }
                    panel["x"] = 0
                    panel["y"] = 0

            sheets.append(current_sheet)
            return sheets

        result_sheets = pack()
        total_sheet_area = len(result_sheets) * sheet_dim["w"] * sheet_dim["h"]
        total_used_area = sum(s["used_area"] for s in result_sheets)
        waste_pct = ((total_sheet_area - total_used_area) / total_sheet_area) * 100

        return {
            "total_sheets": len(result_sheets),
            "waste_percentage": round(waste_pct, 2),
            "sheet_layouts": result_sheets,
            "padding_applied": self.offset
        }
