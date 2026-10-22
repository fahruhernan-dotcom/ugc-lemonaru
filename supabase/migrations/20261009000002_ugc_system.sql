-- =============================================================================
-- VELORA AI: AI Fashion Affiliate UGC Production Engine - Full Schema
-- Migration: 20261009000002_ugc_system.sql
-- Description: Complete schema for Products, Scores, Briefs, Media, Generations, and Events
-- Supports both service_role and anon public access
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. Table: affiliate_products
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.affiliate_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id VARCHAR(128) NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category VARCHAR(128) NOT NULL DEFAULT 'fashion',
    price_idr NUMERIC(15, 2) NOT NULL CHECK (price_idr > 0),
    commission_rate NUMERIC(6, 4) NOT NULL CHECK (commission_rate >= 0 AND commission_rate <= 1.0),
    commission_amount_idr NUMERIC(15, 2) GENERATED ALWAYS AS (price_idr * commission_rate) STORED,
    sales_count INT DEFAULT 0 CHECK (sales_count >= 0),
    rating NUMERIC(3, 2) CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5.0)),
    shop_name VARCHAR(255) NOT NULL,
    stock_available INT DEFAULT 0 CHECK (stock_available >= 0),
    affiliate_url TEXT,
    image_urls JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'out_of_stock', 'blacklisted')),
    raw_payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_affiliate_products_category ON public.affiliate_products (category);
CREATE INDEX IF NOT EXISTS idx_affiliate_products_status ON public.affiliate_products (status);
CREATE INDEX IF NOT EXISTS idx_affiliate_products_created_at ON public.affiliate_products (created_at DESC);

-- -----------------------------------------------------------------------------
-- 2. Table: product_scores
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.product_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES public.affiliate_products(id) ON DELETE CASCADE,
    commission_attractiveness NUMERIC(5, 2) NOT NULL CHECK (commission_attractiveness BETWEEN 0 AND 100),
    commission_stability NUMERIC(5, 2) NOT NULL CHECK (commission_stability BETWEEN 0 AND 100),
    sales_velocity NUMERIC(5, 2) NOT NULL CHECK (sales_velocity BETWEEN 0 AND 100),
    creator_reputation NUMERIC(5, 2) NOT NULL CHECK (creator_reputation BETWEEN 0 AND 100),
    niche_fit NUMERIC(5, 2) NOT NULL CHECK (niche_fit BETWEEN 0 AND 100),
    content_adaptability NUMERIC(5, 2) NOT NULL CHECK (content_adaptability BETWEEN 0 AND 100),
    final_score NUMERIC(5, 2) NOT NULL CHECK (final_score BETWEEN 0 AND 100),
    is_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    ineligibility_reasons JSONB DEFAULT '[]'::jsonb,
    score_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    scoring_version VARCHAR(32) NOT NULL DEFAULT 'v1.0',
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_scores_product_id ON public.product_scores (product_id);
CREATE INDEX IF NOT EXISTS idx_product_scores_final_score ON public.product_scores (final_score DESC);

-- -----------------------------------------------------------------------------
-- 3. Table: product_media
-- Physical product photo references, isolated cutouts, and crops
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.product_media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES public.affiliate_products(id) ON DELETE CASCADE,
    media_type VARCHAR(64) NOT NULL DEFAULT 'catalog_image', -- catalog_image, clean_crop, chin_down, isolated_white_bg
    file_path TEXT NOT NULL,
    storage_provider VARCHAR(32) NOT NULL DEFAULT 'local_drive_d', -- local_drive_d, supabase_storage
    public_url TEXT,
    dimensions JSONB DEFAULT '{"width": 0, "height": 0}'::jsonb,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_media_product_id ON public.product_media (product_id);
CREATE INDEX IF NOT EXISTS idx_product_media_type ON public.product_media (media_type);

-- -----------------------------------------------------------------------------
-- 4. Table: content_briefs
-- Strategic content brief and dynamic copywriting generated per product
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.content_briefs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES public.affiliate_products(id) ON DELETE CASCADE,
    product_score_id UUID REFERENCES public.product_scores(id) ON DELETE SET NULL,
    hook_type VARCHAR(64) NOT NULL,
    hook_text TEXT NOT NULL,
    script_body TEXT NOT NULL,
    shot_list JSONB NOT NULL DEFAULT '[]'::jsonb,
    product_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
    cta_text TEXT NOT NULL,
    caption TEXT NOT NULL,
    hashtags JSONB NOT NULL DEFAULT '[]'::jsonb,
    asset_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    target_aspect_ratio VARCHAR(16) NOT NULL DEFAULT '9:16',
    estimated_duration_seconds INT NOT NULL DEFAULT 10,
    package_export_path TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'ready_for_production', 'producing', 'completed', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_briefs_product_id ON public.content_briefs (product_id);
CREATE INDEX IF NOT EXISTS idx_content_briefs_status ON public.content_briefs (status);

-- -----------------------------------------------------------------------------
-- 5. Table: ugc_generations
-- Generated video renders, audio tracks, prompts, and performance scores
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ugc_generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brief_id UUID NOT NULL REFERENCES public.content_briefs(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES public.affiliate_products(id) ON DELETE CASCADE,
    model_name VARCHAR(64) NOT NULL DEFAULT 'google_flow_omni_flash_1.1',
    prompt_used TEXT NOT NULL,
    reference_image_id UUID REFERENCES public.product_media(id) ON DELETE SET NULL,
    video_path TEXT,
    voiceover_path TEXT,
    duration_seconds NUMERIC(5, 2) DEFAULT 10.0,
    quality_score NUMERIC(4, 2) DEFAULT 8.50, -- e.g. 8.5/10 benchmark
    quality_notes TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'draft' CHECK (status IN ('queued', 'rendering', 'completed', 'failed', 'approved')),
    package_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ugc_generations_brief_id ON public.ugc_generations (brief_id);
CREATE INDEX IF NOT EXISTS idx_ugc_generations_product_id ON public.ugc_generations (product_id);
CREATE INDEX IF NOT EXISTS idx_ugc_generations_status ON public.ugc_generations (status);

-- -----------------------------------------------------------------------------
-- 6. Table: workflow_events
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.workflow_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(64) NOT NULL,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor VARCHAR(64) NOT NULL DEFAULT 'ugc_pipeline_engine',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_events_aggregate ON public.workflow_events (aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS idx_workflow_events_type ON public.workflow_events (event_type);
CREATE INDEX IF NOT EXISTS idx_workflow_events_created_at ON public.workflow_events (created_at DESC);

-- -----------------------------------------------------------------------------
-- Row Level Security (RLS) Configuration - Allow both service_role & anon
-- -----------------------------------------------------------------------------
ALTER TABLE public.affiliate_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_media ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ugc_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_events ENABLE ROW LEVEL SECURITY;

-- 1. affiliate_products
DROP POLICY IF EXISTS service_role_all_affiliate_products ON public.affiliate_products;
CREATE POLICY service_role_all_affiliate_products ON public.affiliate_products FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS anon_all_affiliate_products ON public.affiliate_products;
CREATE POLICY anon_all_affiliate_products ON public.affiliate_products FOR ALL TO anon USING (true) WITH CHECK (true);

-- 2. product_scores
DROP POLICY IF EXISTS service_role_all_product_scores ON public.product_scores;
CREATE POLICY service_role_all_product_scores ON public.product_scores FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS anon_all_product_scores ON public.product_scores;
CREATE POLICY anon_all_product_scores ON public.product_scores FOR ALL TO anon USING (true) WITH CHECK (true);

-- 3. product_media
DROP POLICY IF EXISTS service_role_all_product_media ON public.product_media;
CREATE POLICY service_role_all_product_media ON public.product_media FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS anon_all_product_media ON public.product_media;
CREATE POLICY anon_all_product_media ON public.product_media FOR ALL TO anon USING (true) WITH CHECK (true);

-- 4. content_briefs
DROP POLICY IF EXISTS service_role_all_content_briefs ON public.content_briefs;
CREATE POLICY service_role_all_content_briefs ON public.content_briefs FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS anon_all_content_briefs ON public.content_briefs;
CREATE POLICY anon_all_content_briefs ON public.content_briefs FOR ALL TO anon USING (true) WITH CHECK (true);

-- 5. ugc_generations
DROP POLICY IF EXISTS service_role_all_ugc_generations ON public.ugc_generations;
CREATE POLICY service_role_all_ugc_generations ON public.ugc_generations FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS anon_all_ugc_generations ON public.ugc_generations;
CREATE POLICY anon_all_ugc_generations ON public.ugc_generations FOR ALL TO anon USING (true) WITH CHECK (true);

-- 6. workflow_events
DROP POLICY IF EXISTS service_role_all_workflow_events ON public.workflow_events;
CREATE POLICY service_role_all_workflow_events ON public.workflow_events FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS anon_all_workflow_events ON public.workflow_events;
CREATE POLICY anon_all_workflow_events ON public.workflow_events FOR ALL TO anon USING (true) WITH CHECK (true);

