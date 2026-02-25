from typing import Dict, Any, List

class ACPEngine:
    """
    Automates the technical 'Invisible BOQ' for ACP Cladding.
    """
    def __init__(self, return_allowance_mm: float = 50.0):
        self.offset = return_allowance_mm

    def process_cassette(self, visible_w: float, visible_h: float) -> Dict[str, Any]:
        """
        Adds 50mm fold depth to all 4 sides.
        Calculates sub-frame requirements based on net area.
        """
        cassette_w = visible_w + (2 * self.offset)
        cassette_h = visible_h + (2 * self.offset)
        cassette_area_sqm = (cassette_w * cassette_h) / 1e6
        perimeter_m = (2 * (cassette_w + cassette_h)) / 1000

        return {
            "cassette_size": {"w": cassette_w, "h": cassette_h},
            "net_area_sqm": cassette_area_sqm,
            "sub_frame": {
                "t_profile_mtr": round(cassette_area_sqm * 1.5, 2),
                "l_angle_brackets": round(cassette_area_sqm * 2, 0)
            },
            "sealant_liters": round(perimeter_m * 0.15, 2) # Estimate 0.15L per linear meter of joint
        }
