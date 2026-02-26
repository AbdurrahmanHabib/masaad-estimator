"""
BOM Explosion Engine — generates line-item Bill of Materials from opening schedule.

For each opening (width × height × system_type), queries catalog_items to find
matched profile item_codes and explodes them into quantities using parametric formulas.

Fallback: if no catalog items matched, uses standard UAE facade industry ratios.
"""
import logging
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("masaad-bom")


# ── Standard material ratios (fallback when no catalog match) ─────────────────
# Based on UAE facade industry norms for aluminum curtain wall / window systems

SYSTEM_RATIOS: Dict[str, Dict] = {
    "Curtain Wall": {
        "aluminum_kg_sqm": 12.5,       # kg of aluminum extrusion per SQM
        "glass_sqm_per_sqm": 0.85,     # 85% glazing ratio
        "silicone_ml_per_lm": 120,     # structural silicone per linear metre
        "setting_block_per_sqm": 4,    # EPDM setting blocks
        "spacer_lm_per_sqm": 1.2,      # thermal spacer bar
        "labor_hr_per_sqm": 3.5,       # fabrication hours
    },
    "Sliding Door": {
        "aluminum_kg_sqm": 9.8,
        "glass_sqm_per_sqm": 0.80,
        "silicone_ml_per_lm": 80,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.0,
        "labor_hr_per_sqm": 4.2,
    },
    "Casement Window": {
        "aluminum_kg_sqm": 11.2,
        "glass_sqm_per_sqm": 0.78,
        "silicone_ml_per_lm": 80,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.0,
        "labor_hr_per_sqm": 4.8,
    },
    "Fixed Window": {
        "aluminum_kg_sqm": 8.5,
        "glass_sqm_per_sqm": 0.88,
        "silicone_ml_per_lm": 100,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.1,
        "labor_hr_per_sqm": 2.8,
    },
    "ACP Cladding": {
        "aluminum_kg_sqm": 6.0,        # sub-frame only (ACP itself priced separately)
        "glass_sqm_per_sqm": 0.0,
        "silicone_ml_per_lm": 60,
        "setting_block_per_sqm": 0,
        "spacer_lm_per_sqm": 0,
        "labor_hr_per_sqm": 2.2,
    },
    "DEFAULT": {
        "aluminum_kg_sqm": 10.0,
        "glass_sqm_per_sqm": 0.82,
        "silicone_ml_per_lm": 100,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.0,
        "labor_hr_per_sqm": 3.5,
    },
}

# Attic stock factor (Blind Spot Rule: 2% added to all quantities)
ATTIC_STOCK_PCT = 0.02


@dataclass
class BOMLineItem:
    item_code: str
    description: str
    category: str           # ALUMINUM | GLASS | HARDWARE | SILICONE | LABOR
    unit: str               # kg / sqm / lm / nr / hr
    quantity: float
    unit_cost_aed: float = 0.0
    subtotal_aed: float = 0.0
    is_attic_stock: bool = False
    source_opening_id: str = ""
    notes: str = ""


class BOMEngine:

    def explode_opening(
        self,
        opening: Dict[str, Any],
        catalog_items: List[Dict[str, Any]],
        lme_aed_per_kg: float = 7.0,
        labor_burn_rate: float = 13.0,
    ) -> List[BOMLineItem]:
        """
        Explode a single opening into BOM line items.

        Args:
            opening: dict with keys: id, width_mm, height_mm, system_type, quantity
            catalog_items: list of CatalogItem dicts for this tenant
            lme_aed_per_kg: current LME aluminum price in AED/kg
            labor_burn_rate: fully burdened labor rate in AED/hr

        Returns:
            List of BOMLineItem objects
        """
        width_mm = float(opening.get("width_mm", 1000))
        height_mm = float(opening.get("height_mm", 2000))
        qty = int(opening.get("quantity", 1))
        system_type = opening.get("system_type", "DEFAULT")
        opening_id = str(opening.get("id", ""))

        width_m = width_mm / 1000
        height_m = height_mm / 1000
        sqm_each = width_m * height_m
        sqm_total = sqm_each * qty
        perimeter_m = 2 * (width_m + height_m) * qty

        # Get ratio for this system type (fuzzy match)
        ratio = self._get_ratio(system_type)
        items: List[BOMLineItem] = []

        # ── Aluminum extrusions ───────────────────────────────────────────────
        alum_kg = round(sqm_total * ratio["aluminum_kg_sqm"], 3)
        alum_catalog = [c for c in catalog_items if c.get("material_type") == "ALUMINUM_EXTRUSION"]

        if alum_catalog:
            # Distribute across matched catalog profiles
            profiles_for_system = self._match_profiles(alum_catalog, system_type)
            if profiles_for_system:
                kg_per_profile = alum_kg / len(profiles_for_system)
                for profile in profiles_for_system:
                    weight_per_m = float(profile.get("weight_per_meter") or profile.get("weight_kg_m") or 1.5)
                    length_m = round(kg_per_profile / weight_per_m, 3)
                    unit_cost = float(profile.get("price_aed_per_kg") or lme_aed_per_kg * 1.35)
                    items.append(BOMLineItem(
                        item_code=profile.get("item_code", "ALU-UNKNOWN"),
                        description=profile.get("description") or profile.get("system_series", ""),
                        category="ALUMINUM",
                        unit="lm",
                        quantity=length_m,
                        unit_cost_aed=unit_cost * weight_per_m,
                        subtotal_aed=round(length_m * unit_cost * weight_per_m, 2),
                        source_opening_id=opening_id,
                    ))
            else:
                # Generic aluminum line item
                unit_cost = lme_aed_per_kg * 1.35  # LME + extrusion + coating margin
                items.append(BOMLineItem(
                    item_code="ALU-GENERIC",
                    description=f"Aluminum extrusion — {system_type}",
                    category="ALUMINUM",
                    unit="kg",
                    quantity=alum_kg,
                    unit_cost_aed=unit_cost,
                    subtotal_aed=round(alum_kg * unit_cost, 2),
                    source_opening_id=opening_id,
                    notes="Generic — no catalog profile matched",
                ))
        else:
            unit_cost = lme_aed_per_kg * 1.35
            items.append(BOMLineItem(
                item_code="ALU-GENERIC",
                description=f"Aluminum extrusion — {system_type}",
                category="ALUMINUM",
                unit="kg",
                quantity=alum_kg,
                unit_cost_aed=unit_cost,
                subtotal_aed=round(alum_kg * unit_cost, 2),
                source_opening_id=opening_id,
                notes="No catalog loaded",
            ))

        # ── Glass ─────────────────────────────────────────────────────────────
        glass_sqm = round(sqm_total * ratio["glass_sqm_per_sqm"], 3)
        if glass_sqm > 0:
            glass_catalog = [c for c in catalog_items if c.get("material_type") == "GLASS_PERFORMANCE"]
            glass_unit_cost = 185.0  # AED/sqm default
            glass_item_code = "GLS-GENERIC"
            glass_desc = "Performance glazing (DGU)"
            if glass_catalog:
                g = glass_catalog[0]
                glass_unit_cost = float(g.get("price_aed_sqm") or 185.0)
                glass_item_code = g.get("item_code", "GLS-CATALOG")
                glass_desc = g.get("glass_makeup") or g.get("description") or glass_desc
            items.append(BOMLineItem(
                item_code=glass_item_code,
                description=glass_desc,
                category="GLASS",
                unit="sqm",
                quantity=glass_sqm,
                unit_cost_aed=glass_unit_cost,
                subtotal_aed=round(glass_sqm * glass_unit_cost, 2),
                source_opening_id=opening_id,
            ))

        # ── Silicone (structural + weatherseal) ───────────────────────────────
        silicone_ml = round(perimeter_m * ratio["silicone_ml_per_lm"])
        silicone_tubes = math.ceil(silicone_ml / 600)  # 600ml per tube
        if silicone_tubes > 0:
            items.append(BOMLineItem(
                item_code="SIL-STRUCTURAL",
                description="Structural silicone sealant (600ml)",
                category="SILICONE",
                unit="nr",
                quantity=float(silicone_tubes),
                unit_cost_aed=28.0,
                subtotal_aed=round(silicone_tubes * 28.0, 2),
                source_opening_id=opening_id,
            ))

        # ── EPDM setting blocks ───────────────────────────────────────────────
        setting_blocks = round(sqm_total * ratio["setting_block_per_sqm"])
        if setting_blocks > 0:
            items.append(BOMLineItem(
                item_code="HW-EPDM-BLOCK",
                description="EPDM setting block 100×28×6mm",
                category="HARDWARE",
                unit="nr",
                quantity=float(setting_blocks),
                unit_cost_aed=3.5,
                subtotal_aed=round(setting_blocks * 3.5, 2),
                source_opening_id=opening_id,
            ))

        # ── Thermal spacer bar ────────────────────────────────────────────────
        spacer_lm = round(sqm_total * ratio["spacer_lm_per_sqm"], 2)
        if spacer_lm > 0:
            items.append(BOMLineItem(
                item_code="HW-SPACER-BAR",
                description="Warm-edge spacer bar (stainless)",
                category="HARDWARE",
                unit="lm",
                quantity=spacer_lm,
                unit_cost_aed=12.0,
                subtotal_aed=round(spacer_lm * 12.0, 2),
                source_opening_id=opening_id,
            ))

        # ── Labor ─────────────────────────────────────────────────────────────
        labor_hrs = round(sqm_total * ratio["labor_hr_per_sqm"], 2)
        items.append(BOMLineItem(
            item_code="LABOR-FAB",
            description=f"Fabrication labor — {system_type}",
            category="LABOR",
            unit="hr",
            quantity=labor_hrs,
            unit_cost_aed=labor_burn_rate,
            subtotal_aed=round(labor_hrs * labor_burn_rate, 2),
            source_opening_id=opening_id,
        ))

        # ── Attic stock (+2% on material quantities) ──────────────────────────
        attic_items = []
        for item in items:
            if item.category in ("ALUMINUM", "GLASS", "HARDWARE", "SILICONE"):
                attic_qty = round(item.quantity * ATTIC_STOCK_PCT, 4)
                if attic_qty > 0:
                    attic_items.append(BOMLineItem(
                        item_code=item.item_code + "-ATTIC",
                        description=f"Attic stock 2% — {item.description}",
                        category=item.category,
                        unit=item.unit,
                        quantity=attic_qty,
                        unit_cost_aed=item.unit_cost_aed,
                        subtotal_aed=round(attic_qty * item.unit_cost_aed, 2),
                        is_attic_stock=True,
                        source_opening_id=opening_id,
                        notes="Blind Spot: 2% attic stock per company policy",
                    ))
        items.extend(attic_items)

        return items

    def explode_all(
        self,
        openings: List[Dict[str, Any]],
        catalog_items: List[Dict[str, Any]],
        lme_aed_per_kg: float = 7.0,
        labor_burn_rate: float = 13.0,
    ) -> List[Dict[str, Any]]:
        """
        Explode all openings and return aggregated BOM as list of dicts.
        """
        all_items: List[BOMLineItem] = []
        for opening in openings:
            try:
                items = self.explode_opening(opening, catalog_items, lme_aed_per_kg, labor_burn_rate)
                all_items.extend(items)
            except Exception as e:
                logger.error(f"BOM explosion failed for opening {opening.get('id')}: {e}")

        return [self._item_to_dict(i) for i in all_items]

    def aggregate_by_item_code(self, bom_items: List[Dict]) -> List[Dict]:
        """Roll up duplicate item_codes into single lines with summed quantities."""
        rolled: Dict[str, Dict] = {}
        for item in bom_items:
            code = item["item_code"]
            if code not in rolled:
                rolled[code] = dict(item)
            else:
                rolled[code]["quantity"] = round(rolled[code]["quantity"] + item["quantity"], 4)
                rolled[code]["subtotal_aed"] = round(
                    rolled[code]["quantity"] * rolled[code]["unit_cost_aed"], 2
                )
        return list(rolled.values())

    def _get_ratio(self, system_type: str) -> Dict:
        for key in SYSTEM_RATIOS:
            if key.lower() in system_type.lower() or system_type.lower() in key.lower():
                return SYSTEM_RATIOS[key]
        return SYSTEM_RATIOS["DEFAULT"]

    def _match_profiles(self, catalog: List[Dict], system_type: str) -> List[Dict]:
        """Return catalog profiles that match the given system type."""
        matches = []
        system_lower = system_type.lower()
        for item in catalog:
            series = (item.get("system_series") or "").lower()
            desc = (item.get("description") or "").lower()
            if any(kw in series or kw in desc for kw in ["mullion", "transom", "frame", "sill", "head"]):
                matches.append(item)
        return matches[:6]  # cap at 6 profiles per opening type

    def _item_to_dict(self, item: BOMLineItem) -> Dict:
        return {
            "item_code": item.item_code,
            "description": item.description,
            "category": item.category,
            "unit": item.unit,
            "quantity": item.quantity,
            "unit_cost_aed": item.unit_cost_aed,
            "subtotal_aed": item.subtotal_aed,
            "is_attic_stock": item.is_attic_stock,
            "source_opening_id": item.source_opening_id,
            "notes": item.notes,
        }
