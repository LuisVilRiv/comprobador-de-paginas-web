-- ════════════════════════════════════════════════════════════════════════════
--  web_auditor — Esquema de base de datos
--  Ejecutado automáticamente por PostgreSQL en el primer arranque del
--  contenedor (docker-entrypoint-initdb.d).
-- ════════════════════════════════════════════════════════════════════════════

-- ── Extensiones ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()

-- ════════════════════════════════════════════════════════════════════════════
--  CLIENTES
--  Cada cliente puede tener una o varias páginas web monitorizadas.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS clients (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    email       TEXT,
    phone       TEXT,
    company     TEXT,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE clients IS 'Registro de clientes. Cada cliente puede tener N páginas web.';

-- ════════════════════════════════════════════════════════════════════════════
--  PÁGINAS WEB
--  Equivale al antiguo urls.json, pero en base de datos.
--  Un registro por URL a monitorizar.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS websites (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID        NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    url             TEXT        NOT NULL UNIQUE,
    label           TEXT,                       -- nombre amigable para el dashboard
    strategy        TEXT        NOT NULL DEFAULT 'auto'
                                CHECK (strategy IN ('selenium','beautifulsoup','auto')),
    active          BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_websites_client  ON websites(client_id);
CREATE INDEX IF NOT EXISTS idx_websites_active  ON websites(active);

COMMENT ON TABLE websites IS 'Páginas web a auditar. Vinculadas a un cliente.';

-- ════════════════════════════════════════════════════════════════════════════
--  ANÁLISIS (RUNS)
--  Cada vez que el scraper procesa una URL se crea un registro de ejecución.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_runs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id      UUID        NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running'
                                CHECK (status IN ('running','success','error')),
    strategy_used   TEXT,
    error_message   TEXT,

    -- ── Puntuación y estado global ─────────────────────────────────────────
    score           SMALLINT    CHECK (score BETWEEN 0 AND 100),
    previous_score  SMALLINT    CHECK (previous_score BETWEEN 0 AND 100),
    audit_status    TEXT,                       -- excelente | bueno | mejorable | crítico
    release_blocked BOOLEAN     DEFAULT FALSE,
    audit_date      DATE        NOT NULL DEFAULT CURRENT_DATE,
    sections_passed SMALLINT    NOT NULL DEFAULT 0,
    sections_total  SMALLINT    NOT NULL DEFAULT 10,

    -- ── Métricas de la página ─────────────────────────────────────────────
    response_time_ms    INTEGER,
    status_code         INTEGER,
    word_count          INTEGER,
    h1_count            SMALLINT,
    image_count         SMALLINT,
    links_count         SMALLINT,
    forms_count         SMALLINT,

    -- ── Contadores de incidencias por categoría ───────────────────────────
    security_issue_count    SMALLINT DEFAULT 0,
    seo_issue_count         SMALLINT DEFAULT 0,
    content_issue_count     SMALLINT DEFAULT 0,
    image_issue_count       SMALLINT DEFAULT 0,
    structure_issue_count   SMALLINT DEFAULT 0,
    link_issue_count        SMALLINT DEFAULT 0,
    button_issue_count      SMALLINT DEFAULT 0,
    technical_issue_count   SMALLINT DEFAULT 0,

    -- ── Informe completo en JSON (para el histórico detallado) ────────────
    report_json     JSONB,

    -- ── Texto plano del informe ───────────────────────────────────────────
    report_text     TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_website    ON audit_runs(website_id);
CREATE INDEX IF NOT EXISTS idx_runs_started    ON audit_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status     ON audit_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_score      ON audit_runs(score);

COMMENT ON TABLE audit_runs IS 'Histórico de análisis. Un registro por ejecución del scraper sobre una URL.';

-- ════════════════════════════════════════════════════════════════════════════
--  RESULTADOS POR SECCIÓN DE AUDITORÍA
--  Estado detallado por cada apartado evaluado (10 secciones estándar).
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_run_sections (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              UUID        NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    section_key         TEXT        NOT NULL,
    section_label       TEXT        NOT NULL,
    passed              BOOLEAN     NOT NULL,
    status              TEXT        NOT NULL CHECK (status IN ('ok','warning','failed')),
    issue_count         INTEGER     NOT NULL DEFAULT 0,
    check_description   TEXT        NOT NULL,
    result_description  TEXT        NOT NULL,
    details_json        JSONB       DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, section_key)
);

CREATE INDEX IF NOT EXISTS idx_run_sections_run     ON audit_run_sections(run_id);
CREATE INDEX IF NOT EXISTS idx_run_sections_key     ON audit_run_sections(section_key);
CREATE INDEX IF NOT EXISTS idx_run_sections_passed  ON audit_run_sections(passed);

COMMENT ON TABLE audit_run_sections IS 'Resultado por sección de auditoría para cada ejecución.';

-- ════════════════════════════════════════════════════════════════════════════
--  INCIDENCIAS INDIVIDUALES
--  Cada issue detectado por el auditor se guarda como fila para poder
--  filtrar, comparar entre ejecuciones y visualizar tendencias.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_issues (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID        NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    category    TEXT        NOT NULL,   -- security | seo | content | image | structure | link | button | technical
    severity    TEXT        NOT NULL DEFAULT 'info'
                            CHECK (severity IN ('critical','high','medium','low','info','ok')),
    message     TEXT        NOT NULL,
    line_no     INTEGER,
    line_hint   TEXT
);

CREATE INDEX IF NOT EXISTS idx_issues_run      ON audit_issues(run_id);
CREATE INDEX IF NOT EXISTS idx_issues_category ON audit_issues(category);
CREATE INDEX IF NOT EXISTS idx_issues_severity ON audit_issues(severity);

COMMENT ON TABLE audit_issues IS 'Incidencias individuales de cada análisis.';


-- ════════════════════════════════════════════════════════════════════════════
--  DATOS DE EJEMPLO
--  Clientes y páginas de demo para arrancar el dashboard con contenido.
--  Eliminar o ajustar antes de usar en producción.
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO clients (name, email, company, notes) VALUES
    ('Demo Cliente A', 'cliente-a@ejemplo.com', 'Empresa Alpha S.L.',   'Cliente de prueba para desarrollo'),
    ('Demo Cliente B', 'cliente-b@ejemplo.com', 'Beta Consulting S.A.', 'Agencia con múltiples webs'),
    ('Demo Cliente C', 'cliente-c@ejemplo.com', 'Gamma Store Online',   'E-commerce')
ON CONFLICT DO NOTHING;

INSERT INTO websites (client_id, url, label, strategy, active)
SELECT id, 'https://quotes.toscrape.com/',    'Quotes Scrape',     'beautifulsoup', TRUE  FROM clients WHERE name = 'Demo Cliente A'
ON CONFLICT DO NOTHING;

INSERT INTO websites (client_id, url, label, strategy, active)
SELECT id, 'https://quotes.toscrape.com/js/', 'Quotes JS',         'selenium',      TRUE  FROM clients WHERE name = 'Demo Cliente A'
ON CONFLICT DO NOTHING;

INSERT INTO websites (client_id, url, label, strategy, active)
SELECT id, 'https://books.toscrape.com/',     'Books Scrape',      'beautifulsoup', TRUE  FROM clients WHERE name = 'Demo Cliente B'
ON CONFLICT DO NOTHING;

INSERT INTO websites (client_id, url, label, strategy, active)
SELECT id, 'https://luisvilriv.github.io/',   'Portfolio Personal','selenium',      TRUE  FROM clients WHERE name = 'Demo Cliente C'
ON CONFLICT DO NOTHING;
