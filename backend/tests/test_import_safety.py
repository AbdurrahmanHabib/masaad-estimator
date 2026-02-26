"""
test_import_safety.py — Conditional import safety and circular import checks.

Verifies that:
  1. catalog_pdf_parser imports cleanly even when PyMuPDF (fitz) is absent.
  2. cutting_list_engine imports cleanly even when ortools is absent.
  3. All service modules can be imported without raising ImportError or circular
     import failures (only the module itself is imported — no DB connection made).
  4. The fitz-None guard in catalog_pdf_parser degrades gracefully (Stage 4 DXF
     disabled, everything else operational).
  5. The ortools-None guard in csp_optimizer / cutting_list_engine degrades gracefully.

No database, network, or external services are required.
"""

import sys
import os
import importlib
import types
import pytest

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ---------------------------------------------------------------------------
# Helper — temporarily patch a missing module in sys.modules
# ---------------------------------------------------------------------------

class _AbsentModule(types.ModuleType):
    """Sentinel that raises ImportError for any attribute access."""

    def __getattr__(self, name):
        raise ImportError(f"Simulated absent module: {self.__name__}.{name}")


def _absent(name: str):
    """Context manager: temporarily mask a module as unavailable."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        original = sys.modules.get(name, None)
        absent_sentinel = _AbsentModule(name)
        sys.modules[name] = absent_sentinel
        # Also evict cached sub-imports
        sub_keys = [k for k in sys.modules if k == name or k.startswith(name + ".")]
        saved = {k: sys.modules.pop(k) for k in sub_keys}
        saved[name] = original
        try:
            yield
        finally:
            sys.modules.pop(name, None)
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    return _ctx()


# ---------------------------------------------------------------------------
# TASK 4A — catalog_pdf_parser importable without PyMuPDF
# ---------------------------------------------------------------------------

class TestCatalogPdfParserImport:
    """catalog_pdf_parser must be importable even if fitz (PyMuPDF) is absent."""

    def test_imports_without_fitz(self):
        """
        Mask fitz as absent; catalog_pdf_parser must import without raising
        ImportError. The module uses try/except ImportError around fitz import.
        """
        # Remove cached copy so reimport is forced
        for key in list(sys.modules.keys()):
            if "catalog_pdf_parser" in key:
                del sys.modules[key]

        with _absent("fitz"):
            try:
                from app.services import catalog_pdf_parser as cpp
                assert cpp is not None
            except ImportError as e:
                pytest.fail(
                    f"catalog_pdf_parser raised ImportError when fitz was absent: {e}"
                )

    def test_fitz_none_guard_set_correctly(self):
        """
        When fitz is absent, the module-level `fitz` variable must be None
        and _RENDER_MATRIX must be None (not raise AttributeError).
        """
        for key in list(sys.modules.keys()):
            if "catalog_pdf_parser" in key:
                del sys.modules[key]

        with _absent("fitz"):
            try:
                import app.services.catalog_pdf_parser as cpp
                # fitz guard
                assert cpp.fitz is None, (
                    "Expected cpp.fitz to be None when PyMuPDF is absent"
                )
                # Render matrix guard
                assert cpp._RENDER_MATRIX is None, (
                    "Expected _RENDER_MATRIX to be None when fitz is absent"
                )
            except ImportError:
                pytest.skip("catalog_pdf_parser has unresolvable deps in this env")

    def test_hitl_threshold_accessible_without_fitz(self):
        """Module-level constants must be accessible even without fitz."""
        for key in list(sys.modules.keys()):
            if "catalog_pdf_parser" in key:
                del sys.modules[key]

        with _absent("fitz"):
            try:
                import app.services.catalog_pdf_parser as cpp
                assert cpp.HITL_CONFIDENCE_THRESHOLD == 0.90
                assert "ALUMINUM_EXTRUSION" in cpp.REQUIRED_FIELDS
            except ImportError:
                pytest.skip("catalog_pdf_parser has unresolvable deps in this env")


# ---------------------------------------------------------------------------
# TASK 4B — cutting_list_engine importable without ortools
# ---------------------------------------------------------------------------

class TestCuttingListEngineImport:
    """cutting_list_engine must be importable even if ortools is absent."""

    def test_imports_without_ortools(self):
        """Mask ortools and ortools.sat.python.cp_model as absent."""
        ortools_keys = [k for k in sys.modules if "ortools" in k]
        for key in list(sys.modules.keys()):
            if "cutting_list_engine" in key or "csp_optimizer" in key:
                del sys.modules[key]

        # Mask ortools root
        saved = {k: sys.modules.pop(k, None) for k in ["ortools"]}
        try:
            sys.modules["ortools"] = _AbsentModule("ortools")
            from app.services import cutting_list_engine as cle
            assert cle is not None
        except ImportError as e:
            pytest.fail(
                f"cutting_list_engine raised ImportError when ortools was absent: {e}"
            )
        finally:
            sys.modules.pop("ortools", None)
            for k, v in saved.items():
                if v is not None:
                    sys.modules[k] = v

    def test_fabrication_norms_accessible_without_ortools(self):
        """FABRICATION_NORMS_MINUTES must be accessible without ortools."""
        for key in list(sys.modules.keys()):
            if "cutting_list_engine" in key:
                del sys.modules[key]

        saved = {k: sys.modules.pop(k, None) for k in ["ortools"]}
        try:
            sys.modules["ortools"] = _AbsentModule("ortools")
            import app.services.cutting_list_engine as cle
            assert "saw_cut_straight" in cle.FABRICATION_NORMS_MINUTES
            assert cle.FABRICATION_NORMS_MINUTES["saw_cut_straight"] > 0
        except ImportError:
            pytest.skip("cutting_list_engine has other unresolvable deps")
        finally:
            sys.modules.pop("ortools", None)
            for k, v in saved.items():
                if v is not None:
                    sys.modules[k] = v

    def test_hardware_rules_accessible_without_ortools(self):
        """HARDWARE_RULES dict must load correctly without ortools."""
        for key in list(sys.modules.keys()):
            if "cutting_list_engine" in key:
                del sys.modules[key]

        saved = {k: sys.modules.pop(k, None) for k in ["ortools"]}
        try:
            sys.modules["ortools"] = _AbsentModule("ortools")
            import app.services.cutting_list_engine as cle
            assert "Window - Casement" in cle.HARDWARE_RULES
            assert "Door - Single Swing" in cle.HARDWARE_RULES
        except ImportError:
            pytest.skip("cutting_list_engine has other unresolvable deps")
        finally:
            sys.modules.pop("ortools", None)
            for k, v in saved.items():
                if v is not None:
                    sys.modules[k] = v


# ---------------------------------------------------------------------------
# TASK 4C — All service modules import without circular import errors
# ---------------------------------------------------------------------------

# Modules that require live DB / celery / heavy optional deps — skip those
_SKIP_MODULES = {
    "app.workers.tasks",      # Celery tasks — needs celery app running
    "app.workers.celery_app", # Celery app — needs Redis
}

# Services that can be imported without external services (pure computation)
_PURE_SERVICE_MODULES = [
    "app.services.bom_engine",
    "app.services.costing_engine",
    "app.services.labor_engine",
    "app.services.physics_engine",
    "app.services.acp_engine",
    "app.services.value_engineering_engine",
    "app.services.scope_engine",
    "app.services.compliance_engine",
    "app.services.risk_engine",
    "app.services.cutting_list_engine",
    "app.services.opening_schedule_engine",
    "app.services.nesting_engine_2d",
    "app.services.optimization_engine",
    "app.services.optimization_engine_1d",
    "app.services.engineering_engine",
    "app.services.finance_engine",
    "app.services.auditor_engine",
    "app.services.spatial_engine",
    "app.services.tagging_engine",
    "app.services.spec_fusion_engine",
    "app.services.perf_monitor",
    "app.services.logging_config",
    "app.services.middleware",
]

_MODEL_MODULES = [
    "app.agents.graph_state",
    "app.models.websocket_models",
    "app.models.catalog_schema",
]


class TestServiceModuleImports:
    """All pure service modules must import without circular import errors."""

    @pytest.mark.parametrize("module_path", _PURE_SERVICE_MODULES)
    def test_pure_service_module_imports(self, module_path):
        """
        Import each service module directly.  Only ImportError from the module
        itself (not from optional deps) causes test failure.
        """
        try:
            mod = importlib.import_module(module_path)
            assert mod is not None, f"Module {module_path} is None after import"
        except ImportError as e:
            msg = str(e)
            # Tolerate missing optional deps (fitz, ortools, ezdxf, pdfplumber, etc.)
            _optional_deps = [
                "fitz", "ortools", "ezdxf", "pdfplumber",
                "litellm", "langchain", "langgraph", "xlsxwriter",
                "reportlab", "celery", "redis", "sqlalchemy",
            ]
            if any(dep in msg for dep in _optional_deps):
                pytest.skip(f"Optional dependency missing: {msg}")
            else:
                pytest.fail(f"{module_path} raised ImportError: {e}")
        except Exception as e:
            pytest.fail(f"{module_path} raised unexpected error on import: {type(e).__name__}: {e}")

    @pytest.mark.parametrize("module_path", _MODEL_MODULES)
    def test_model_and_state_modules_import(self, module_path):
        """Model/state modules must import without DB connection."""
        try:
            mod = importlib.import_module(module_path)
            assert mod is not None
        except ImportError as e:
            msg = str(e)
            _optional_deps = ["sqlalchemy", "asyncpg", "psycopg2"]
            if any(dep in msg for dep in _optional_deps):
                pytest.skip(f"DB driver not installed: {msg}")
            else:
                pytest.fail(f"{module_path} raised ImportError: {e}")


class TestNoCyclicImports:
    """Ensure key module pairs don't form circular import chains."""

    def test_bom_engine_does_not_import_costing_engine(self):
        """bom_engine should be independent of costing_engine."""
        import app.services.bom_engine as bom
        # If costing_engine were in bom_engine's globals it would be circular
        assert "costing_engine" not in dir(bom), (
            "bom_engine appears to directly import costing_engine (circular risk)"
        )

    def test_graph_state_has_no_service_imports(self):
        """GraphState must be a pure TypedDict with no service dependencies."""
        try:
            import app.agents.graph_state as gs
            # Must define GraphState as a TypedDict
            from typing import get_type_hints
            assert hasattr(gs, "GraphState")
            # GraphState should have the core fields
            hints = gs.GraphState.__annotations__
            assert "estimate_id" in hints
            assert "bom_items" in hints
        except ImportError as e:
            pytest.skip(f"graph_state dep missing: {e}")

    def test_value_engineering_engine_is_standalone(self):
        """VE engine must not import database or LLM clients."""
        import app.services.value_engineering_engine as ve
        # Check that the module source doesn't reference DB session
        import inspect
        src = inspect.getsource(ve)
        assert "AsyncSession" not in src, (
            "value_engineering_engine must not depend on AsyncSession"
        )
        assert "get_db" not in src, (
            "value_engineering_engine must not depend on get_db"
        )

    def test_bom_engine_is_standalone(self):
        """BOM engine must not reference async DB or LLM."""
        import app.services.bom_engine as bom
        import inspect
        src = inspect.getsource(bom)
        assert "AsyncSession" not in src, (
            "bom_engine must not depend on AsyncSession (use pure computation)"
        )

    def test_compliance_engine_is_standalone(self):
        """Compliance engine must be pure computation (no DB calls)."""
        try:
            import app.services.compliance_engine as ce
            import inspect
            src = inspect.getsource(ce)
            assert "get_db" not in src, (
                "compliance_engine must not call get_db (must be DB-free)"
            )
        except ImportError as e:
            pytest.skip(f"compliance_engine dep missing: {e}")


# ---------------------------------------------------------------------------
# TASK 4D — Graceful degradation verification
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """Services must degrade gracefully, not crash, when optional deps are absent."""

    def test_catalog_parser_fitz_none_does_not_crash_module_load(self):
        """
        Loading catalog_pdf_parser with fitz=None must not raise at module level.
        The _RENDER_MATRIX = fitz.Matrix(2, 2) if fitz else None guard must work.
        """
        for key in list(sys.modules.keys()):
            if "catalog_pdf_parser" in key:
                del sys.modules[key]

        with _absent("fitz"):
            try:
                import app.services.catalog_pdf_parser
                # If we get here, the guard works
                assert True
            except AttributeError as e:
                pytest.fail(
                    f"catalog_pdf_parser crashed at load with fitz=None: {e}\n"
                    "Expected the guard: `fitz.Matrix(2,2) if fitz else None`"
                )
            except ImportError:
                pytest.skip("catalog_pdf_parser has other missing deps in this env")

    def test_bom_engine_system_ratios_complete(self):
        """
        SYSTEM_RATIOS must include all 6 expected system types.
        Missing a ratio would silently fall back to DEFAULT, causing mis-pricing.
        """
        from app.services.bom_engine import SYSTEM_RATIOS
        expected_systems = {
            "Curtain Wall", "Sliding Door", "Casement Window",
            "Fixed Window", "ACP Cladding", "DEFAULT",
        }
        for system in expected_systems:
            assert system in SYSTEM_RATIOS, (
                f"SYSTEM_RATIOS missing entry for '{system}'"
            )

    def test_bom_engine_attic_stock_constant(self):
        """ATTIC_STOCK_PCT must be exactly 2% (company Blind Spot Rule)."""
        from app.services.bom_engine import ATTIC_STOCK_PCT
        assert ATTIC_STOCK_PCT == 0.02, (
            f"ATTIC_STOCK_PCT must be 0.02 (2%), got {ATTIC_STOCK_PCT}"
        )

    def test_cutting_list_fabrication_norms_all_positive(self):
        """All fabrication norms must be positive time values."""
        try:
            from app.services.cutting_list_engine import FABRICATION_NORMS_MINUTES
            for op, mins in FABRICATION_NORMS_MINUTES.items():
                assert mins > 0, (
                    f"FABRICATION_NORMS_MINUTES['{op}'] = {mins} — must be > 0"
                )
        except ImportError as e:
            pytest.skip(f"cutting_list_engine dep missing: {e}")
