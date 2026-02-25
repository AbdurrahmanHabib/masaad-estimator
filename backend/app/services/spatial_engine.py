from typing import List, Dict, Any
import numpy as np

class ElevationMapper:
    """
    Groups facade entities into Cardinal Zones (E1-E4) based on coordinate clustering.
    """
    def map_to_zones(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        zones = {"E1_EAST": [], "E2_WEST": [], "E3_NORTH": [], "E4_SOUTH": []}
        
        for entity in entities:
            pos = entity.get('position', (0, 0))
            rotation = entity.get('rotation', 0)
            
            # Simple Cardinal Logic based on Block Rotation in CAD
            if 45 <= rotation < 135:
                zones["E3_NORTH"].append(entity)
            elif 135 <= rotation < 225:
                zones["E2_WEST"].append(entity)
            elif 225 <= rotation < 315:
                zones["E4_SOUTH"].append(entity)
            else:
                zones["E1_EAST"].append(entity)
                
        return zones

class SlabEdgeCalculator:
    """
    Calculates distance between Concrete Slab and Mullion for Bracket Sizing.
    """
    def calculate_bracket_offset(self, slab_coord: float, mullion_coord: float) -> float:
        # Standard calculation: Offset = Abs Distance - Profile Depth
        offset = abs(slab_coord - mullion_coord)
        
        # Auto-Size MS Brackets (UAE Factory Standard Sizes)
        if offset < 100: return 80.0  # 80mm standard bracket
        if offset < 150: return 120.0 # 120mm standard bracket
        return offset - 20.0 # Custom Fabrication required