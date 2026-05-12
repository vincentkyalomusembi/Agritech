-- =============================================================================
-- db/schema.sql
-- Supabase (PostgreSQL) schema for Agritech AI.
--
-- Run once in the Supabase SQL editor or via psql:
--   psql $DATABASE_URL -f db/schema.sql
--
-- Tables
-- ------
--   users            — farmer profiles (one row per MSISDN)
--   subscriptions    — plan & billing state tied to a user
--   vets             — registered veterinary officers
--   agri_officers    — registered agricultural extension officers
--   county_profiles  — climate & soil data for all 47 Kenyan counties
--
-- Auth strategy
-- -------------
-- phone_number is the primary identity key (matches Africa's Talking MSISDN).
-- Row-Level Security (RLS) is enabled on every table.
-- Service-role key (used by the FastAPI backend) bypasses RLS.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()


-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    phone         TEXT        NOT NULL UNIQUE,           -- +2547XXXXXXXX (E.164)
    name          TEXT,
    county        TEXT,
    farm_type     TEXT CHECK (farm_type IN ('crop', 'livestock', NULL)),
    soil_type     TEXT,
    onboarded     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Keep updated_at fresh automatically
CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

-- Index for phone lookups (most common query pattern)
CREATE INDEX IF NOT EXISTS users_phone_idx ON public.users (phone);

-- RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access" ON public.users
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------------------
-- subscriptions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    plan        TEXT        NOT NULL DEFAULT 'free'
                            CHECK (plan IN ('free', 'basic', 'pro')),
    status      TEXT        NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'cancelled', 'expired', 'trial')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ                              -- NULL = never expires
);

CREATE INDEX IF NOT EXISTS subs_user_id_idx ON public.subscriptions (user_id);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access" ON public.subscriptions
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------------------
-- vets
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.vets (
    id           UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT  NOT NULL,
    phone        TEXT  NOT NULL UNIQUE,
    county       TEXT,
    speciality   TEXT,
    license_no   TEXT,
    available    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS vets_county_idx ON public.vets (county);

ALTER TABLE public.vets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access" ON public.vets
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------------------
-- agri_officers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agri_officers (
    id           UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT  NOT NULL,
    phone        TEXT  NOT NULL UNIQUE,
    county       TEXT,
    ward         TEXT,
    employee_id  TEXT,
    available    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS officers_county_idx ON public.agri_officers (county);

ALTER TABLE public.agri_officers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access" ON public.agri_officers
    USING (true) WITH CHECK (true);


-- ---------------------------------------------------------------------------
-- county_profiles
-- Replaces seed_data.csv. One row per (county, farm_type) → 94 rows total
-- (47 counties × 2 farm types). Populated by:  python -m db.seed
--
-- Sources
-- -------
--   avg_rainfall, avg_temp : Kenya Meteorological Dept normals 1981–2010
--   soil_type              : KALRO county soil-profile reports (2018/2019)
--   recommendation         : KALRO "Recommended Varieties & Husbandry Practices"
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.county_profiles (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    county           TEXT         NOT NULL,
    soil_type        TEXT         NOT NULL
                                  CHECK (soil_type IN ('sandy', 'loamy', 'clay', 'peaty')),
    avg_rainfall     INT          NOT NULL,        -- mm, annual mean
    avg_temp         NUMERIC(4,1) NOT NULL,        -- °C, annual mean
    farm_type        TEXT         NOT NULL
                                  CHECK (farm_type IN ('crop', 'livestock')),
    recommendation   TEXT         NOT NULL,
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- Upsert key: one row per (county, farm_type)
    UNIQUE (county, farm_type)
);

-- Fast county lookups (used on every USSD recommendation request)
CREATE INDEX IF NOT EXISTS county_profiles_county_idx
    ON public.county_profiles (county);

ALTER TABLE public.county_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access" ON public.county_profiles
    USING (true) WITH CHECK (true);
