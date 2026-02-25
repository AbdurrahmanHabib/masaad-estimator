from pydantic import BaseModel, Field
from typing import Optional

class MaterialCatalogItem(BaseModel):
    """
    Standardized Supplier Catalog Schema for Madinat Al Saada.
    Enforces strict float types for physical properties.
    """
    Supplier_Name: str = Field(..., description="e.g., Gulf Extrusions")
    System_Series: str = Field(..., description="e.g., GE-F, GE-C")
    Die_Number: str = Field(..., description="The primary search key for the DWG Parser")
    Description: Optional[str] = Field(None, description="e.g., Mullion, Transom")
    Weight_kg_m: float = Field(..., description="Linear weight in kg per meter")
    Perimeter_mm: float = Field(..., description="Total exposed surface for finishing costs")
    Scrap_Value_Factor: float = Field(1.0, description="Recyclability index (1.0 = 100%)")

# SQL Schema Preview for Migration:
# CREATE TABLE materials_catalog (
#     die_number VARCHAR(100) PRIMARY KEY,
#     supplier_name VARCHAR(255),
#     system_series VARCHAR(100),
#     description TEXT,
#     weight_kg_m DECIMAL(10, 4) NOT NULL,
#     perimeter_mm DECIMAL(10, 2) NOT NULL,
#     scrap_value_factor DECIMAL(5, 2) DEFAULT 1.0,
#     tenant_id UUID,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );
