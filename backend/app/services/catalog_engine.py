from typing import List, Dict, Any
import pandas as pd
import logging

logger = logging.getLogger("masaad-api")

class CatalogEngine:
    """
    Performs the join between geometric truth (DWG) and material metadata.
    """
    def map_dwg_to_catalog(self, dwg_entities: List[Dict[str, Any]], catalog_df: pd.DataFrame) -> Dict[str, Any]:
        mapped_entities = []
        rfis = []
        
        # Ensure Die_Number is the index for O(1) lookup
        catalog_lookup = catalog_df.set_index('Die_Number')
        
        for entity in dwg_entities:
            # The 'die_tag' is extracted from DWG layers or block attributes
            die_tag = entity.get('die_number')
            
            if die_tag in catalog_lookup.index:
                material_meta = catalog_lookup.loc[die_tag]
                
                # Merge geometric data with physical catalog data
                mapped_entities.append({
                    **entity,
                    "weight_kg_m": float(material_meta['Weight_kg_m']),
                    "perimeter_mm": float(material_meta['Perimeter_mm']),
                    "scrap_factor": float(material_meta.get('Scrap_Value_Factor', 1.0)),
                    "system_series": material_meta['System_Series'],
                    "is_mapped": True
                })
            else:
                # Flag missing items for the Senior Estimator
                rfis.append({
                    "system_tag": die_tag,
                    "entity_id": entity.get('id'),
                    "issue": "MISSING_FROM_CATALOG",
                    "action_required": f"Update catalog with physical properties for Die: {die_tag}"
                })
                mapped_entities.append({
                    **entity,
                    "is_mapped": False,
                    "rfi_id": f"MISSING_{die_tag}"
                })
                
        return {
            "mapped_data": mapped_entities,
            "rfi_count": len(rfis),
            "rfi_details": rfis,
            "validation_passed": len(rfis) == 0
        }