from typing import Dict, Any

class ACPEngine:
    """
    Precision Cladding Production Engine.
    Ensures 'Invisible' costs are captured before fabrication.
    """
    def __init__(self, fold_mm: float = 50.0):
        self.fold = fold_mm

    def get_production_specs(self, width: float, height: float) -> Dict[str, Any]:
        # 1. Automatic 50mm Fold Return on all 4 sides
        cas_w = width + (2 * self.fold)
        cas_h = height + (2 * self.fold)
        area_sqm = (cas_w * cas_h) / 1e6

        # 2. Hidden Aluminum Skeleton (Carrier Frame)
        # 1.5m vertical T-profiles and 2 brackets per SQM
        frame_mtr = round(area_sqm * 1.5, 2)
        brackets = round(area_sqm * 2, 0)

        return {
            "production_size": {"width": cas_w, "height": cas_h},
            "net_weight_kg": round(area_sqm * 5.5, 2), # Typical 4mm ACP weight
            "carrier_frame": {
                "t_profile_mtr": frame_mtr,
                "l_brackets_pcs": int(brackets)
            },
            "status": "Production_Optimized"
        }
