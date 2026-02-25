from typing import Dict, Any

class PhysicsEngine:
    """
    Automates the 'Invisible Skeleton' quantification.
    Maps primary detected items to their structural dependencies.
    """
    def generate_acp_skeleton(self, net_sqm: float, perimeter_m: float) -> Dict[str, Any]:
        """
        For every SQM of ACP, calculates the sub-frame and sealing components.
        """
        return {
            "aluminum_t_profile_mtr": round(net_sqm * 1.8, 2), # Vertical Runners @ 600mm
            "aluminum_l_angle_mtr": round(net_sqm * 1.2, 2),   # Horizontal Bracing
            "fixing_brackets_pcs": round(net_sqm * 4.5, 0),    # Runner Brackets
            "backer_rod_mtr": round(perimeter_m, 2),
            "weather_silicone_tubes": round(perimeter_m / 6.0, 0) # 6m per tube
        }

    def generate_mullion_anchor_kit(self, mullion_count: int) -> Dict[str, Any]:
        """
        Calculates heavy-duty anchoring for Curtain Wall mullions.
        """
        return {
            "hilti_anchor_bolts": int(mullion_count * 4),
            "ms_galvanized_brackets": int(mullion_count * 1),
            "joint_sleeves": int(mullion_count * 0.5)
        }
