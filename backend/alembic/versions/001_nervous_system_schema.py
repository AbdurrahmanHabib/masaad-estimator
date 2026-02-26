"""nervous_system_schema

Revision ID: 001_nervous_system
Revises:
Create Date: 2026-02-26

Adds tables and columns for:
- triage_queue (HITL items)
- smart_profile_dies (DXF die registry)
- catalog_items: material_type, glass fields, procurement fields
- financial_rates: baseline_labor_burn_rate_aed, burn_rate fields
- estimates: approved_by, approved_at, bom_snapshot_json, revision_number

All DDL uses IF NOT EXISTS / try-except patterns so the migration is
idempotent — safe to run even when Base.metadata.create_all() already
created the tables.
"""
import logging
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = '001_nervous_system'
down_revision = None
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.001")


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT EXISTS("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_name = :tname"
            ")"
        ),
        {"tname": table_name},
    )
    return bool(result.scalar())


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT EXISTS("
            "  SELECT 1 FROM information_schema.columns"
            "  WHERE table_name = :tname AND column_name = :cname"
            ")"
        ),
        {"tname": table_name, "cname": column_name},
    )
    return bool(result.scalar())


def upgrade() -> None:
    conn = op.get_bind()

    # ── triage_queue ──────────────────────────────────────────────────────────
    if not _table_exists(conn, 'triage_queue'):
        op.create_table(
            'triage_queue',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
            sa.Column('estimate_id', sa.String(36), nullable=True, index=True),
            sa.Column('node_name', sa.String(100), nullable=False),
            sa.Column('confidence_score', sa.Float, nullable=False, server_default='0.0'),
            sa.Column('context_json', sa.Text, nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('resolution_json', sa.Text, nullable=True),
            sa.Column('resolved_by', sa.String(36), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        )
        logger.info("Created table: triage_queue")
    else:
        logger.info("Table triage_queue already exists — skipping create")

    # ── smart_profile_dies ────────────────────────────────────────────────────
    if not _table_exists(conn, 'smart_profile_dies'):
        op.create_table(
            'smart_profile_dies',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
            sa.Column('item_code', sa.String(100), nullable=False),
            sa.Column('die_number', sa.String(50), nullable=False),
            sa.Column('system_series', sa.String(100), nullable=True),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('dxf_path', sa.Text, nullable=True),
            sa.Column('anchor_origin_xy', sa.String(50), nullable=True),
            sa.Column('glazing_pocket_xy', sa.String(50), nullable=True),
            sa.Column('bead_snap_xy', sa.String(50), nullable=True),
            sa.Column('max_glass_thickness', sa.Numeric(6, 2), nullable=True),
            sa.Column('bounding_box_polygon', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint('tenant_id', 'item_code', name='uq_smart_die_item_code'),
        )
        logger.info("Created table: smart_profile_dies")
    else:
        logger.info("Table smart_profile_dies already exists — skipping create")

    # ── catalog_items: new columns ────────────────────────────────────────────
    _catalog_cols = [
        ('material_type', sa.Column('material_type', sa.String(50), server_default='ALUMINUM_EXTRUSION')),
        ('u_value_w_m2k', sa.Column('u_value_w_m2k', sa.Numeric(6, 3), nullable=True)),
        ('shading_coefficient_sc', sa.Column('shading_coefficient_sc', sa.Numeric(5, 3), nullable=True)),
        ('visible_light_transmittance_vlt', sa.Column('visible_light_transmittance_vlt', sa.Numeric(5, 3), nullable=True)),
        ('acoustic_rating_rw_db', sa.Column('acoustic_rating_rw_db', sa.Integer, nullable=True)),
        ('glass_makeup', sa.Column('glass_makeup', sa.String(200), nullable=True)),
        ('fire_rating_minutes', sa.Column('fire_rating_minutes', sa.Integer, nullable=True)),
        ('supplier_name', sa.Column('supplier_name', sa.String(200), nullable=True)),
        ('lead_time_days', sa.Column('lead_time_days', sa.Integer, nullable=True)),
        ('supplier_payment_terms', sa.Column('supplier_payment_terms', sa.String(100), nullable=True)),
        ('minimum_order_qty', sa.Column('minimum_order_qty', sa.Numeric(10, 2), nullable=True)),
    ]
    if _table_exists(conn, 'catalog_items'):
        with op.batch_alter_table('catalog_items') as batch_op:
            for col_name, col_def in _catalog_cols:
                if not _column_exists(conn, 'catalog_items', col_name):
                    batch_op.add_column(col_def)
                    logger.info(f"Added column catalog_items.{col_name}")
    else:
        logger.warning("Table catalog_items does not exist — skipping column additions")

    # ── financial_rates: new columns ──────────────────────────────────────────
    _finance_cols = [
        ('baseline_labor_burn_rate_aed', sa.Column('baseline_labor_burn_rate_aed', sa.Numeric(8, 2), server_default='13.00')),
        ('burn_rate_last_updated', sa.Column('burn_rate_last_updated', sa.DateTime(timezone=True), nullable=True)),
        ('burn_rate_updated_by_source', sa.Column('burn_rate_updated_by_source', sa.String(100), nullable=True)),
        ('lme_aluminum_usd_mt', sa.Column('lme_aluminum_usd_mt', sa.Numeric(10, 2), nullable=True)),
        ('lme_last_fetched', sa.Column('lme_last_fetched', sa.DateTime(timezone=True), nullable=True)),
        ('lme_source', sa.Column('lme_source', sa.String(50), nullable=True)),
    ]
    if _table_exists(conn, 'financial_rates'):
        with op.batch_alter_table('financial_rates') as batch_op:
            for col_name, col_def in _finance_cols:
                if not _column_exists(conn, 'financial_rates', col_name):
                    batch_op.add_column(col_def)
                    logger.info(f"Added column financial_rates.{col_name}")
    else:
        logger.warning("Table financial_rates does not exist — skipping column additions")

    # ── estimates: new columns ────────────────────────────────────────────────
    _estimate_cols = [
        ('approved_by', sa.Column('approved_by', sa.String(36), nullable=True)),
        ('approved_at', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True)),
        ('bom_snapshot_json', sa.Column('bom_snapshot_json', sa.Text, nullable=True)),
        ('revision_number', sa.Column('revision_number', sa.Integer, server_default='0')),
        ('state_snapshot', sa.Column('state_snapshot', sa.Text, nullable=True)),
    ]
    if _table_exists(conn, 'estimates'):
        with op.batch_alter_table('estimates') as batch_op:
            for col_name, col_def in _estimate_cols:
                if not _column_exists(conn, 'estimates', col_name):
                    batch_op.add_column(col_def)
                    logger.info(f"Added column estimates.{col_name}")
    else:
        logger.warning("Table estimates does not exist — skipping column additions")


def downgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, 'smart_profile_dies'):
        op.drop_table('smart_profile_dies')
    if _table_exists(conn, 'triage_queue'):
        op.drop_table('triage_queue')

    if _table_exists(conn, 'estimates'):
        with op.batch_alter_table('estimates') as batch_op:
            for col in ['approved_by', 'approved_at', 'bom_snapshot_json', 'revision_number', 'state_snapshot']:
                if _column_exists(conn, 'estimates', col):
                    batch_op.drop_column(col)

    if _table_exists(conn, 'financial_rates'):
        with op.batch_alter_table('financial_rates') as batch_op:
            for col in ['baseline_labor_burn_rate_aed', 'burn_rate_last_updated', 'burn_rate_updated_by_source', 'lme_aluminum_usd_mt', 'lme_last_fetched', 'lme_source']:
                if _column_exists(conn, 'financial_rates', col):
                    batch_op.drop_column(col)

    if _table_exists(conn, 'catalog_items'):
        with op.batch_alter_table('catalog_items') as batch_op:
            for col in ['material_type', 'u_value_w_m2k', 'shading_coefficient_sc', 'visible_light_transmittance_vlt', 'acoustic_rating_rw_db', 'glass_makeup', 'fire_rating_minutes', 'supplier_name', 'lead_time_days', 'supplier_payment_terms', 'minimum_order_qty']:
                if _column_exists(conn, 'catalog_items', col):
                    batch_op.drop_column(col)
