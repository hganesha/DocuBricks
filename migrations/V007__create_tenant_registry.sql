CREATE TABLE IF NOT EXISTS tenant_registry (
    tenant_id       TEXT        PRIMARY KEY,
    tenant_name     TEXT        NOT NULL,
    vertical        TEXT        NOT NULL,
    tier            TEXT        NOT NULL DEFAULT 'community',
    status          TEXT        NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at    TIMESTAMPTZ,
    owner_email     TEXT        NOT NULL,
    CONSTRAINT valid_tier   CHECK (tier IN ('community','starter','professional','enterprise')),
    CONSTRAINT valid_status CHECK (status IN ('PENDING','ACTIVE','SUSPENDED','OFFBOARDED'))
);

CREATE TABLE IF NOT EXISTS tenant_reviewer_assignments (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT        NOT NULL REFERENCES tenant_registry(tenant_id),
    vertical        TEXT        NOT NULL,
    reviewer_email  TEXT        NOT NULL,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, vertical, reviewer_email)
);

CREATE TABLE IF NOT EXISTS tenant_users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT        NOT NULL REFERENCES tenant_registry(tenant_id),
    user_email      TEXT        NOT NULL,
    role            TEXT        NOT NULL DEFAULT 'viewer',
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    added_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_role CHECK (role IN ('viewer','reviewer','admin')),
    UNIQUE (tenant_id, user_email)
);

CREATE TABLE IF NOT EXISTS onboarding_sessions (
    onboarding_id   TEXT        PRIMARY KEY,
    tenant_id       TEXT,
    state           TEXT        NOT NULL DEFAULT 'WELCOME',
    config          JSONB,
    deploy_log      JSONB,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tenant_users_email
    ON tenant_users (user_email) WHERE is_active = TRUE;
