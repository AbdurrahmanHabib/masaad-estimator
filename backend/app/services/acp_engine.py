from typing import Dict, Any

class ACPEngine:
    """
    Automates Cladding Production Logic.
    """
    def __init__(self, return_mm: float = 50.0):
        self.return_mm = return_mm

    def calculate_production_requirements(self, width: float, height: float) -> Dict[str, Any]:
        # 1. Cassette Sizing (Adding 50mm to all 4 sides)
        cassette_w = width + (2 * self.return_mm)
        cassette_h = height + (2 * self.return_mm)
        area_sqm = (cassette_w * cassette_h) / 1e6

        # 2. Hidden Carrier Frame (Industrial Rule of Thumb)
        # 1.5 linear meters of T-Profile and 2 brackets per SQM
        t_profile_mtr = round(area_sqm * 1.5, 2)
        l_angle_brackets = round(area_sqm * 2, 0)

        return {
            "cassette_size": {"w": cassette_w, "h": cassette_h},
            "area_sqm": area_sqm,
            "carrier_frame": {
                "t_profile_mtr": t_profile_mtr,
                "l_angle_brackets": int(l_angle_brackets)
            }
        }
