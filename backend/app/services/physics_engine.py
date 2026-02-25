from typing import Dict, Any, List

class PhysicsEngine:
    """
    Automates the 'Invisible BOQ' based on engineering dependencies.
    """
    def explode_acp_dependencies(self, net_sqm: float, linear_mtr_joints: float) -> Dict[str, Any]:
        """
        Calculates sub-frames and fixings for every SQM of ACP.
        """
        return {
            "aluminum_sub_frame_mtr": round(net_sqm * 2.8, 2), # Based on 600mm grid
            "fixing_brackets": round(net_sqm * 4.5, 0),       # Runner/Starter brackets
            "weather_silicone_tubes": round(linear_mtr_joints / 6.0, 0), # 6m per tube
            "cleats_and_rivets": round(net_sqm * 12, 0)
        }

    def explode_mullion_dependencies(self, mullion_count: int) -> Dict[str, Any]:
        """
        Calculates bolts and brackets per mullion connection.
        """
        return {
            "hilti_anchor_bolts": mullion_count * 4,
            "ms_galvanized_brackets": mullion_count * 1,
            "epdm_joint_gaskets": mullion_count * 0.5 # linear meters
        }
