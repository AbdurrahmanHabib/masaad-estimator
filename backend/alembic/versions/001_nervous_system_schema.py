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
"""
from alembic import op
import sqlalchemy as sa

revision = '001_nervous_system'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── triage_queue ──────────────────────────────────────────────────────────
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

    # ── smart_profile_dies ────────────────────────────────────────────────────
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

    # ── catalog_items: new columns ────────────────────────────────────────────
    with op.batch_alter_table('catalog_items') as batch_op:
        batch_op.add_column(sa.Column('material_type', sa.String(50), server_default='ALUMINUM_EXTRUSION'))
        batch_op.add_column(sa.Column('u_value_w_m2k', sa.Numeric(6, 3), nullable=True))
        batch_op.add_column(sa.Column('shading_coefficient_sc', sa.Numeric(5, 3), nullable=True))
        batch_op.add_column(sa.Column('visible_light_transmittance_vlt', sa.Numeric(5, 3), nullable=True))
        batch_op.add_column(sa.Column('acoustic_rating_rw_db', sa.Integer, nullable=True))
        batch_op.add_column(sa.Column('glass_makeup', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('fire_rating_minutes', sa.Integer, nullable=True))
        batch_op.add_column(sa.Column('supplier_name', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('lead_time_days', sa.Integer, nullable=True))
        batch_op.add_column(sa.Column('supplier_payment_terms', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('minimum_order_qty', sa.Numeric(10, 2), nullable=True))

    # ── financial_rates: new columns ──────────────────────────────────────────
    with op.batch_alter_table('financial_rates') as batch_op:
        batch_op.add_column(sa.Column('baseline_labor_burn_rate_aed', sa.Numeric(8, 2), server_default='13.00'))
        batch_op.add_column(sa.Column('burn_rate_last_updated', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('burn_rate_updated_by_source', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('lme_aluminum_usd_mt', sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column('lme_last_fetched', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('lme_source', sa.String(50), nullable=True))

    # ── estimates: new columns ────────────────────────────────────────────────
    with op.batch_alter_table('estimates') as batch_op:
        batch_op.add_column(sa.Column('approved_by', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('bom_snapshot_json', sa.Text, nullable=True))
        batch_op.add_column(sa.Column('revision_number', sa.Integer, server_default='0'))
        batch_op.add_column(sa.Column('state_snapshot', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_table('smart_profile_dies')
    op.drop_table('triage_queue')
    with op.batch_alter_table('estimates') as batch_op:
        for col in ['approved_by', 'approved_at', 'bom_snapshot_json', 'revision_number', 'state_snapshot']:
            batch_op.drop_column(col)
    with op.batch_alter_table('financial_rates') as batch_op:
        for col in ['baseline_labor_burn_rate_aed', 'burn_rate_last_updated', 'burn_rate_updated_by_source', 'lme_aluminum_usd_mt', 'lme_last_fetched', 'lme_source']:
            batch_op.drop_column(col)
    with op.batch_alter_table('catalog_items') as batch_op:
        for col in ['material_type', 'u_value_w_m2k', 'shading_coefficient_sc', 'visible_light_transmittance_vlt', 'acoustic_rating_rw_db', 'glass_makeup', 'fire_rating_minutes', 'supplier_name', 'lead_time_days', 'supplier_payment_terms', 'minimum_order_qty']:
            batch_op.drop_column(col)
