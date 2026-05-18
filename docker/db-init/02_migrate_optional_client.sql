-- ════════════════════════════════════════════════════════════════════════════
--  MIGRACIÓN: client_id opcional en websites
--  Permite crear URLs sin asociarlas a ningún cliente.
--  Este script es idempotente: puede ejecutarse en una BD ya existente.
-- ════════════════════════════════════════════════════════════════════════════

-- 1. Quitar la restricción NOT NULL de client_id
ALTER TABLE websites
    ALTER COLUMN client_id DROP NOT NULL;

-- 2. Cambiar la acción ON DELETE de CASCADE a SET NULL
--    (primero eliminamos la FK vieja y luego añadimos la nueva)
ALTER TABLE websites
    DROP CONSTRAINT IF EXISTS websites_client_id_fkey;

ALTER TABLE websites
    ADD CONSTRAINT websites_client_id_fkey
        FOREIGN KEY (client_id)
        REFERENCES clients(id)
        ON DELETE SET NULL;
