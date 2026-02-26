"""ORM Models for Masaad Estimator — SQLAlchemy 2.0"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String, Text, Boolean, Integer, Numeric, DateTime, Date,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db import Base


def gen_uuid():
    return str(uuid.uuid4())


# ── TENANTS ──────────────────────────────────────────────────────────────────
class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text)
    primary_color: Mapped[Optional[str]] = mapped_column(String(10), default="#1e293b")
    subscription_tier: Mapped[str] = mapped_column(String(50), default="professional")
    subscription_status: Mapped[str] = mapped_column(String(50), default="active")
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="tenant")


# ── AUTH ──────────────────────────────────────────────────────────────────────
class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="users")
    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="users")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="created_by_user")


# ── FINANCIAL RATES ───────────────────────────────────────────────────────────
class FinancialRates(Base):
    __tablename__ = "financial_rates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    lme_aluminum_usd_mt: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), default=2485.0)
    billet_premium_usd_mt: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), default=400.0)
    extrusion_premium_usd_mt: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), default=800.0)
    usd_aed: Mapped[float] = mapped_column(Numeric(12, 4), default=3.6725)
    eur_aed: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), default=4.02)
    lme_last_fetched: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lme_source: Mapped[str] = mapped_column(String(50), default="cached")
    # Fully burdened labor rate (direct payroll + factory overhead + admin)
    # Pushed from Flask HRMS via POST /api/v1/hrms/update-burn-rate
    baseline_labor_burn_rate_aed: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("13.00")
    )
    burn_rate_last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    burn_rate_updated_by_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual"
    )  # "manual" | "hrms_push" | "payroll_upload"
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))


# ── MATERIAL RATES ────────────────────────────────────────────────────────────
class MaterialRates(Base):
    __tablename__ = "material_rates"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), unique=True)
    # Glass (AED/SQM)
    glass_clear_float_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=65.00)
    glass_tinted_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=75.00)
    glass_tempered_clear_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=85.00)
    glass_tempered_tinted_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=95.00)
    glass_laminated_6_6_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=145.00)
    glass_low_e_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=120.00)
    glass_dgu_6_12_6_clear_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=175.00)
    glass_dgu_low_e_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=225.00)
    glass_opaque_spandrel_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=95.00)
    glass_structural_dgu_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=280.00)
    # ACP (AED/SQM)
    acp_polyester_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=140.00)
    acp_powder_coat_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=160.00)
    acp_pvdf_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=185.00)
    acp_metallic_pvdf_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=210.00)
    acp_mirror_aed_sqm: Mapped[float] = mapped_column(Numeric(10, 2), default=225.00)
    # Hardware (AED/unit)
    hardware_casement_handle_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=85.00)
    hardware_casement_hinge_pair_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=45.00)
    hardware_casement_lock_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=120.00)
    hardware_casement_restrictor_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=28.00)
    hardware_door_handle_set_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=280.00)
    hardware_mortice_lock_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=380.00)
    hardware_door_closer_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=245.00)
    hardware_door_hinge_set_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=65.00)
    hardware_sliding_track_per_lm_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=95.00)
    hardware_sliding_roller_set_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=45.00)
    hardware_floor_spring_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=680.00)
    hardware_patch_fitting_set_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=420.00)
    hardware_spider_fitting_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=580.00)
    # Sealants
    sealant_weatherseal_310ml_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=18.00)
    sealant_structural_600ml_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=35.00)
    sealant_primer_500ml_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=42.00)
    backer_rod_10mm_per_lm_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=1.20)
    backer_rod_15mm_per_lm_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=1.80)
    setting_block_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=1.80)
    distance_piece_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=0.90)
    # Fixings
    anchor_m10_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=6.50)
    anchor_m12_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=8.50)
    bracket_80mm_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=45.00)
    bracket_120mm_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=65.00)
    shim_plate_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=1.50)
    thermal_pad_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=2.20)
    t_connector_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=8.00)
    l_connector_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=6.50)
    end_cap_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=3.50)
    expansion_joint_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=45.00)
    fire_stop_per_lm_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=28.00)
    drainage_insert_each_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=3.50)
    # Labor
    factory_hourly_rate_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=85.00)
    site_installation_rate_aed: Mapped[float] = mapped_column(Numeric(10, 2), default=95.00)
    # Overheads
    factory_overhead_pct: Mapped[float] = mapped_column(Numeric(6, 4), default=0.12)
    admin_overhead_pct: Mapped[float] = mapped_column(Numeric(6, 4), default=0.08)
    risk_contingency_pct: Mapped[float] = mapped_column(Numeric(6, 4), default=0.05)
    default_profit_margin_pct: Mapped[float] = mapped_column(Numeric(6, 4), default=0.15)
    rates_last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))


# ── CATALOG ───────────────────────────────────────────────────────────────────
class CatalogItem(Base):
    __tablename__ = "catalog_items"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    item_code: Mapped[str] = mapped_column(String(100), nullable=False)
    die_number: Mapped[Optional[str]] = mapped_column(String(50))
    system_series: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), default="Profile")
    unit_of_measure: Mapped[str] = mapped_column(String(10), default="m")
    weight_per_meter: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    perimeter_mm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    inertia_ixx: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    inertia_iyy: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    face_dimension_mm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    structural_depth_mm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    glass_rebate_depth_mm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    thermal_break_depth_mm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), default=0)
    is_thermal_break: Mapped[bool] = mapped_column(Boolean, default=False)
    price_aed_per_kg: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    unit_cost_aed: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    price_date: Mapped[Optional[date]] = mapped_column(Date)
    lme_at_price_date: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    price_source: Mapped[Optional[str]] = mapped_column(String(50))
    price_notes: Mapped[Optional[str]] = mapped_column(Text)
    price_absent: Mapped[bool] = mapped_column(Boolean, default=False)
    extraction_method: Mapped[Optional[str]] = mapped_column(String(20))
    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    source_file: Mapped[Optional[str]] = mapped_column(String(255))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    # ── Material Router discriminator ─────────────────────────────────────────
    # ALUMINUM_EXTRUSION | GLASS_PERFORMANCE | HARDWARE
    material_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ALUMINUM_EXTRUSION", index=True
    )
    # ── Glass performance fields (GlassPerformanceSchema) ────────────────────
    u_value_w_m2k: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    shading_coefficient_sc: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    visible_light_transmittance_vlt: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    acoustic_rating_rw_db: Mapped[Optional[int]] = mapped_column(Integer)
    glass_makeup: Mapped[Optional[str]] = mapped_column(String(100))
    # ── Compliance ────────────────────────────────────────────────────────────
    fire_rating_minutes: Mapped[Optional[int]] = mapped_column(Integer)  # 0/30/60/90/120
    # ── Procurement / commercial ─────────────────────────────────────────────
    supplier_name: Mapped[Optional[str]] = mapped_column(String(100))
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer)
    supplier_payment_terms: Mapped[Optional[str]] = mapped_column(String(50))
    minimum_order_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("tenant_id", "item_code", name="uq_catalog_item_code"),)


class ItemDependency(Base):
    __tablename__ = "item_dependencies"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    parent_item_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("catalog_items.id"))
    child_item_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("catalog_items.id"))
    quantity_formula: Mapped[str] = mapped_column(Text, nullable=False)
    logic_conditions: Mapped[Optional[dict]] = mapped_column(JSONB)
    system_type: Mapped[Optional[str]] = mapped_column(String(100))


# ── PROJECTS & ESTIMATES ──────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="Active")
    location_zone: Mapped[Optional[str]] = mapped_column(String(100))
    project_country: Mapped[str] = mapped_column(String(100), default="UAE")
    is_international: Mapped[bool] = mapped_column(Boolean, default=False)
    consultant_name: Mapped[Optional[str]] = mapped_column(String(255))
    contract_type: Mapped[str] = mapped_column(String(50), default="Supply + Fabricate + Install")
    complexity_multiplier: Mapped[float] = mapped_column(Numeric(4, 2), default=1.0)
    scope_boundary: Mapped[str] = mapped_column(String(100), default="Panels + Substructure")
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="projects")
    created_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="projects")
    estimates: Mapped[list["Estimate"]] = relationship("Estimate", back_populates="project")


class Estimate(Base):
    __tablename__ = "estimates"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    status: Mapped[str] = mapped_column(String(50), default="Draft")
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[Optional[str]] = mapped_column(String(255))
    raw_data_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    project_scope_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    opening_schedule_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    bom_output_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    cutting_list_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    glass_schedule_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    financial_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    drawings_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    risk_register_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    value_engineering_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    procurement_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    installation_plan_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    fabrication_plan_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    reasoning_log: Mapped[Optional[list]] = mapped_column(JSONB)
    lme_snapshot_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lme_usd_at_estimate: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    dxf_override_url: Mapped[Optional[str]] = mapped_column(Text)
    state_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB)
    # Approval Gateway — status state machine:
    # Draft → ESTIMATING → REVIEW_REQUIRED → APPROVED → DISPATCHED | Failed
    approved_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    bom_snapshot_json: Mapped[Optional[dict]] = mapped_column(JSONB)  # Rev N snapshot for Delta Engine
    revision_number: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    project: Mapped["Project"] = relationship("Project", back_populates="estimates")


# ── OFFCUT INVENTORY ──────────────────────────────────────────────────────────
class OffcutInventory(Base):
    __tablename__ = "offcut_inventory"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    die_number: Mapped[str] = mapped_column(String(100))
    item_code: Mapped[Optional[str]] = mapped_column(String(100))
    length_mm: Mapped[float] = mapped_column(Numeric(10, 2))
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    source_estimate_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    source_bar_id: Mapped[Optional[str]] = mapped_column(String(50))
    is_consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    consumed_by_estimate_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── CONSULTANT DICTIONARY ─────────────────────────────────────────────────────
class ConsultantDictionary(Base):
    __tablename__ = "consultant_dictionary"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    consultant_name: Mapped[Optional[str]] = mapped_column(String(255))
    raw_layer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mapped_internal_type: Mapped[str] = mapped_column(String(255), nullable=False)
    __table_args__ = (UniqueConstraint("tenant_id", "raw_layer_name", name="uq_dict_layer"),)


# ── HRMS ──────────────────────────────────────────────────────────────────────
class BatchTicket(Base):
    __tablename__ = "batch_tickets"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    work_order_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    estimate_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    system_type: Mapped[Optional[str]] = mapped_column(String(100))
    estimated_hours: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    actual_hours: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductivityMultiplier(Base):
    __tablename__ = "productivity_multipliers"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    system_type: Mapped[str] = mapped_column(String(100), nullable=False)
    multiplier: Mapped[float] = mapped_column(Numeric(8, 4), default=1.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (UniqueConstraint("tenant_id", "system_type", name="uq_productivity_system"),)


# ── HISTORICAL ESTIMATES ──────────────────────────────────────────────────────
class HistoricalEstimate(Base):
    __tablename__ = "historical_estimates"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"))
    project_name: Mapped[Optional[str]] = mapped_column(Text)
    project_type: Mapped[Optional[str]] = mapped_column(String(100))
    project_country: Mapped[Optional[str]] = mapped_column(String(100))
    year_completed: Mapped[Optional[int]] = mapped_column(Integer)
    system_type: Mapped[Optional[str]] = mapped_column(String(100))
    total_sqm: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    total_price_aed: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    unit_rate_aed_sqm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    profit_margin_actual_pct: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── HITL TRIAGE QUEUE ─────────────────────────────────────────────────────────
class TriageItem(Base):
    """
    Human-in-the-Loop triage queue.
    Created when a graph node yields confidence_score < 0.90.
    The graph suspends until the item is resolved via POST /api/v1/triage/resolve/{id}.
    """
    __tablename__ = "triage_queue"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True
    )
    estimate_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    # JSON blob: {"image_b64": "...", "raw_text": "..."}
    context_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending | resolved | skipped
    resolution_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))  # user_id


# ── SMART PROFILE DIES ────────────────────────────────────────────────────────
class SmartProfileDie(Base):
    """
    Die registry for the Parametric Constraint Assembly Engine (DraftingNode).
    Stores constraint metadata (anchors, bounding box) alongside the .dxf block path.
    LLM only reads item_code and system_series; the engine handles all geometry.
    """
    __tablename__ = "smart_profile_dies"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True
    )
    item_code: Mapped[str] = mapped_column(String(100), nullable=False)
    die_number: Mapped[str] = mapped_column(String(50), nullable=False)
    system_series: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    dxf_path: Mapped[Optional[str]] = mapped_column(Text)       # Absolute path on server
    # Constraint metadata (mm, stored as JSON array)
    anchor_origin_xy: Mapped[Optional[str]] = mapped_column(String(50))   # "[x,y]"
    glazing_pocket_xy: Mapped[Optional[str]] = mapped_column(String(50))  # "[x,y]"
    bead_snap_xy: Mapped[Optional[str]] = mapped_column(String(50))       # "[x,y]"
    max_glass_thickness: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    bounding_box_polygon: Mapped[Optional[str]] = mapped_column(Text)     # JSON array of [x,y] pairs
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        UniqueConstraint("tenant_id", "item_code", name="uq_smart_die_item_code"),
    )
