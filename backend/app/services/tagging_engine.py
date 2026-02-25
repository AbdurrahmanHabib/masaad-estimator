from typing import List, Dict, Any
import hashlib

class ExportTagGenerator:
    """
    Generates unique ID strings for international tracking.
    Format: [PROJECT]-[ELEVATION]-[FLOOR]-[SYSTEM]-[SEQUENCE]
    """
    def generate_tag(self, project: str, elev: str, floor: str, sys: str, seq: int) -> str:
        tag = f"{project}-{elev}-F{floor.zfill(2)}-{sys}-{str(seq).zfill(3)}"
        return tag.upper()

    def generate_crate_manifest(self, units: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Groups tags into Container-Ready Crate lists.
        Separates Brackets (First Fix) from Frames (Second Fix).
        """
        manifest = {
            "CRATE_FIX_01_BRACKETS": [],
            "CRATE_FIX_02_FRAMES": [],
            "CRATE_FIX_03_GLASS": []
        }
        
        for unit in units:
            tag = unit['tag']
            manifest["CRATE_FIX_02_FRAMES"].append(tag)
            manifest["CRATE_FIX_01_BRACKETS"].append(f"{tag}-BRKT")
            
        return manifest