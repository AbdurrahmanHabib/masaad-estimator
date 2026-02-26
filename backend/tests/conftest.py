"""
conftest.py — Shared pytest fixtures for the Masaad Estimator backend test suite.

No database or external service fixtures are defined here.  All tests in this
suite are pure unit tests that exercise computation classes in isolation.

Import-path bootstrapping:
    The ``backend/`` directory is inserted into sys.path so that all
    ``app.*`` imports resolve correctly regardless of where pytest is invoked.
"""

import sys
import os
import pytest

# ---------------------------------------------------------------------------
# Ensure ``backend/`` is on the import path before any app imports occur.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ---------------------------------------------------------------------------
# CostingEngine fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def default_costing_engine():
    """
    CostingEngine instantiated with all defaults (no overrides).

    Defaults:
      LME = 2350 USD/mt, billet = 400, extrusion = 800, powder = 15 AED/kg,
      USD/AED = 3.6725, overhead = 12%, margin = 18%, attic = 2%.
    """
    from app.services.costing_engine import CostingEngine
    return CostingEngine()


@pytest.fixture(scope="session")
def custom_costing_engine():
    """
    CostingEngine with explicitly set rates and project config — useful for
    deterministic numeric verification.

    Financial rates:
      LME = 2500 USD/mt, billet = 350, extrusion = 750,
      powder_coating = 14.0 AED/kg, USD/AED = 3.67
    Project config:
      overhead = 12%, margin = 18%, attic = 2%, international = False
    """
    from app.services.costing_engine import CostingEngine
    return CostingEngine(
        financial_rates={
            "lme_usd_mt": 2500.0,
            "billet_premium": 350.0,
            "extrusion_premium": 750.0,
            "powder_coating_aed_kg": 14.0,
            "usd_aed": 3.67,
            "anodizing_aed_kg": 18.0,
            "factory_hourly_rate": 85.0,
        },
        project_config={
            "overhead_pct": 0.12,
            "margin_pct": 0.18,
            "attic_stock_pct": 0.02,
            "is_international": False,
            "provisional_gpr_aed": 15_000.0,
            "provisional_water_test_aed": 8_500.0,
            "provisional_logistics_permits_aed": 5_000.0,
        },
    )


@pytest.fixture(scope="session")
def international_costing_engine():
    """CostingEngine with international mode enabled."""
    from app.services.costing_engine import CostingEngine
    return CostingEngine(
        project_config={"is_international": True},
    )


# ---------------------------------------------------------------------------
# LaborEngine fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def labor_engine():
    """LaborEngine with default settings."""
    from app.services.labor_engine import LaborEngine
    return LaborEngine()


# ---------------------------------------------------------------------------
# PhysicsEngine fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def physics_engine():
    """PhysicsEngine instantiated with no arguments (stateless, pure-math)."""
    from app.services.physics_engine import PhysicsEngine
    return PhysicsEngine()


# ---------------------------------------------------------------------------
# ACPEngine fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def acp_engine():
    """ACPEngine with default 50 mm fold (Madinat Al Saada standard)."""
    from app.services.acp_engine import ACPEngine
    return ACPEngine(fold_mm=50.0)


@pytest.fixture(scope="session")
def acp_engine_30mm():
    """ACPEngine with 30 mm fold — used for non-standard fold geometry tests."""
    from app.services.acp_engine import ACPEngine
    return ACPEngine(fold_mm=30.0)


# ---------------------------------------------------------------------------
# Shared sample BOM data
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_bom():
    """
    A minimal mixed BOM with one item per category — used by full-estimate
    rollup tests to verify the aggregation pipeline end-to-end.

    Note: hardware items must carry a non-zero unit_rate_aed so the engine
    does not coerce 0.0 to None via the ``float(x) or None`` pattern in
    calculate_full_estimate's hardware_bom builder.
    """
    return [
        {
            "category": "aluminium",
            "description": "65x35 mullion profile",
            "weight_kg": 500.0,
        },
        {
            "category": "glass",
            "glass_type": "igu_lowe",
            "area_sqm": 100.0,
            "processing": [],
            "wastage_pct": 0.10,
        },
        {
            "category": "hardware",
            "hardware_type": "handle",
            "quantity": 20.0,
            "unit_rate_aed": 45.0,   # explicit rate avoids float(0.0) or None
        },
        {
            "category": "fabrication",
            "operations": {
                "cnc_cuts": 100,
                "assembly_joints": 50,
            },
        },
        {
            "category": "installation",
            "install_type": "curtain_wall_sqm",
            "quantity": 100.0,
            "height_m": 10.0,
            "unit_rate_aed": 180.0,   # explicit rate avoids float(0.0) or None
        },
    ]


@pytest.fixture
def payroll_entries():
    """
    Sample payroll data for blended-rate and attendance tests.
    Contains entries across FACTORY, SITE, and DESIGN departments.
    """
    return [
        {
            "employee_id": "E001",
            "department": "FACTORY",
            "basic_salary": 2000.0,
            "allowances": 500.0,
            "skill_level": "SKILLED",
        },
        {
            "employee_id": "E002",
            "department": "FACTORY",
            "basic_salary": 1800.0,
            "allowances": 400.0,
            "skill_level": "SEMI_SKILLED",
        },
        {
            "employee_id": "E003",
            "department": "SITE",
            "basic_salary": 2500.0,
            "allowances": 800.0,
            "skill_level": "FOREMAN",
        },
        {
            "employee_id": "E004",
            "department": "DESIGN",
            "basic_salary": 8000.0,
            "allowances": 2000.0,
            "skill_level": "ENGINEER",
        },
    ]
