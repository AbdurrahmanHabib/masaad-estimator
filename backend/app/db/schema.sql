-- Phase 1: Core Database Schema for Masaad Estimator
-- Location: AWS me-south-1 (PostgreSQL 15+)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Identity & Access Management
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL -- 'Admin', 'Senior_Estimator', 'Draftsman'
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role_id INTEGER REFERENCES roles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Financial & Market Logic
CREATE TABLE financial_rates (
    id SERIAL PRIMARY KEY,
    lme_aluminum_base_price_usd DECIMAL(12, 4), -- Live LME
    billet_premium_usd DECIMAL(12, 4),
    exchange_rate_usd_aed DECIMAL(12, 4) DEFAULT 3.6725,
    exchange_rate_eur_aed DECIMAL(12, 4),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. The Knowledge Graph (Systems & Dependencies)
CREATE TABLE catalog_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_code VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'GULF-EXT-7001'
    category VARCHAR(50), -- 'Profile', 'Glass', 'Gasket', 'Hardware'
    description TEXT,
    unit_of_measure VARCHAR(10), -- 'm', 'kg', 'sqm', 'pcs'
    weight_per_meter DECIMAL(10, 4), -- For aluminum profiles
    inertia_ixx DECIMAL(15, 4), -- For structural checks
    inertia_iyy DECIMAL(15, 4),
    unit_cost_aed DECIMAL(12, 4),
    metadata JSONB -- Storage for specific supplier attributes
);

CREATE TABLE item_dependencies (
    parent_item_id UUID REFERENCES catalog_items(id),
    child_item_id UUID REFERENCES catalog_items(id),
    quantity_formula TEXT NOT NULL, -- e.g., '2 * (W + H)' or '1'
    logic_conditions JSONB, -- e.g., {"min_weight": 150, "swap_with": "HW-HEAVY"}
    PRIMARY KEY (parent_item_id, child_item_id)
);

-- 4. Projects & AI Context
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    location_zone VARCHAR(50), -- 'Dubai_Zone_A', 'Abu_Dhabi' (ASCE 7-16 mapping)
    consultant_name VARCHAR(255),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE consultant_dictionary (
    id SERIAL PRIMARY KEY,
    consultant_name VARCHAR(255),
    raw_layer_name VARCHAR(255),
    mapped_internal_type VARCHAR(255), -- e.g., 'A-WIN-EXT' -> 'Mullion'
    UNIQUE(consultant_name, raw_layer_name)
);

-- 5. Estimates & State Persistence
CREATE TABLE estimates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id),
    status VARCHAR(50), -- 'Processing', 'HITL_Review', 'Completed'
    lme_snapshot_at TIMESTAMP WITH TIME ZONE,
    raw_data_json JSONB, -- Stores extracted coordinates and quantities
    bom_output_json JSONB, -- Final exploded Bill of Materials
    state_snapshot JSONB, -- LangGraph Checkpoint State
    dxf_override_url TEXT, -- S3 link to altered CAD file
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE offcut_inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_code VARCHAR(100) REFERENCES catalog_items(item_code),
    length_mm DECIMAL(10, 2),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_consumed BOOLEAN DEFAULT FALSE
);