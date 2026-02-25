-- Phase 3: Knowledge Graph Schema
-- Target: PostgreSQL 15+

-- 1. Component Registry (Already in schema.sql, adding the CTE here)

-- Recursive CTE View for BOM Explosion
CREATE OR REPLACE FUNCTION explode_bom(root_id UUID)
RETURNS TABLE (
    depth INT,
    parent_id UUID,
    child_id UUID,
    item_code VARCHAR,
    unit_of_measure VARCHAR,
    base_cost_aed DECIMAL,
    parametric_logic JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE bom_tree AS (
        -- Anchor Member: Find direct children of the system
        SELECT 
            1 as depth,
            r.parent_id,
            r.child_id,
            c.item_code,
            c.unit_of_measure,
            c.base_cost_aed,
            r.parametric_logic
        FROM item_dependencies r
        JOIN catalog_items c ON r.child_id = c.id
        WHERE r.parent_id = root_id

        UNION ALL

        -- Recursive Member: Find children of children
        SELECT 
            bt.depth + 1,
            r.parent_id,
            r.child_id,
            c.item_code,
            c.unit_of_measure,
            c.base_cost_aed,
            r.parametric_logic
        FROM item_dependencies r
        JOIN catalog_items c ON r.child_id = c.id
        INNER JOIN bom_tree bt ON r.parent_id = bt.child_id
        WHERE bt.depth < 10 -- Safety Limit (as per Master Plan)
    )
    SELECT * FROM bom_tree;
END;
$$ LANGUAGE plpgsql;