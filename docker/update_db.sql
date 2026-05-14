CREATE TABLE IF NOT EXISTS global_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO global_settings (key, value) VALUES 
('cron_active', '"0 0 * * 0,3"'::jsonb),
('cron_inactive', '"0 0 1 2,4,6,8,10,12 *"'::jsonb) 
ON CONFLICT (key) DO NOTHING;
