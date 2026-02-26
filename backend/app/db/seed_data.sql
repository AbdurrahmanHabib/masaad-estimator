-- Masaad Estimator — Seed Data
-- Run after schema creation to populate reference data

-- 1. Roles
INSERT INTO roles (name) VALUES
    ('Admin'),
    ('Senior_Estimator'),
    ('Draftsman'),
    ('Viewer')
ON CONFLICT (name) DO NOTHING;

-- 2. Default tenant (Masaad company)
INSERT INTO tenants (id, name, slug, primary_color, subscription_tier, subscription_status)
VALUES (
    gen_random_uuid(),
    'Madinat Al Saada Aluminium & Glass Works LLC',
    'masaad',
    '#1e293b',
    'enterprise',
    'active'
) ON CONFLICT (slug) DO NOTHING;

-- 3. Financial rates (default LME placeholder)
-- baseline_labor_burn_rate_aed = 13.00 AED (fully burdened: direct payroll + factory overhead + admin)
-- Push updates via POST /api/v1/hrms/update-burn-rate from Flask HRMS
INSERT INTO financial_rates (
    tenant_id, lme_aluminum_usd_mt, billet_premium_usd_mt, extrusion_premium_usd_mt,
    usd_aed, lme_source, baseline_labor_burn_rate_aed, burn_rate_updated_by_source
)
SELECT id, 2485.0, 400.0, 800.0, 3.6725, 'default', 13.00, 'manual'
FROM tenants WHERE slug = 'masaad'
ON CONFLICT DO NOTHING;

-- 4. Material rates for masaad tenant (defaults — admin will update)
INSERT INTO material_rates (tenant_id)
SELECT id FROM tenants WHERE slug = 'masaad'
ON CONFLICT (tenant_id) DO NOTHING;

-- 5. Default admin user (admin@masaad.ae / admin1234)
INSERT INTO users (email, hashed_password, full_name, is_active, tenant_id, role_id)
SELECT
    'admin@masaad.ae',
    '$2b$12$mJcF8vQBFaFZdmwwRUE/D.PXKYyoUMcz7ZAhYVJ4VRY3nqSwfoKDy',
    'Admin',
    TRUE,
    t.id,
    r.id
FROM tenants t, roles r
WHERE t.slug = 'masaad' AND r.name = 'Admin'
ON CONFLICT (email) DO NOTHING;

-- 6. Default consultant dictionary entries (common UAE layer naming conventions)
INSERT INTO consultant_dictionary (tenant_id, consultant_name, raw_layer_name, mapped_internal_type)
SELECT t.id, 'Generic', layer, mapped FROM tenants t, (VALUES
    ('A-CW-EXT', 'Curtain Wall (Stick)'),
    ('A-CW-INT', 'Curtain Wall (Stick)'),
    ('CWALL', 'Curtain Wall (Stick)'),
    ('CURTAIN-WALL', 'Curtain Wall (Stick)'),
    ('A-WIN-01', 'Window - Casement'),
    ('A-WIN-EXT', 'Window - Casement'),
    ('WINDOW', 'Window - Fixed'),
    ('A-DR-01', 'Door - Single Swing'),
    ('A-DR-EXT', 'Door - Single Swing'),
    ('DOOR', 'Door - Single Swing'),
    ('A-ACP-01', 'ACP Cladding'),
    ('A-ACP-EXT', 'ACP Cladding'),
    ('CLADDING', 'ACP Cladding'),
    ('A-GR-01', 'Glass Railing'),
    ('RAILING', 'Glass Railing'),
    ('A-LV-01', 'Louvre System'),
    ('LOUVER', 'Louvre System'),
    ('A-CP-01', 'Canopy'),
    ('CANOPY', 'Canopy'),
    ('A-SS-01', 'Sun Shading (Blades)'),
    ('SUNSHADE', 'Sun Shading (Blades)'),
    ('A-SP-01', 'Spandrel Panel'),
    ('SPANDREL', 'Spandrel Panel'),
    ('A-SG-01', 'Structural Glazing'),
    ('STR-GLAZ', 'Structural Glazing'),
    ('A-SKY-01', 'Skylight'),
    ('SKYLIGHT', 'Skylight'),
    ('A-PAR-01', 'Parapet Coping'),
    ('PARAPET', 'Parapet Coping')
) AS mappings(layer, mapped)
WHERE t.slug = 'masaad'
ON CONFLICT (tenant_id, raw_layer_name) DO NOTHING;
