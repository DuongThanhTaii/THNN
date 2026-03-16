CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    external_id TEXT UNIQUE,
    email TEXT UNIQUE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO users (id, external_id, email, display_name, created_at, updated_at)
SELECT id, external_id, email, display_name, created_at, updated_at
FROM app_users
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('users', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 0) FROM users), 1),
    true
);

ALTER TABLE workspaces
DROP CONSTRAINT IF EXISTS workspaces_owner_user_id_fkey;

ALTER TABLE workspaces
ADD CONSTRAINT workspaces_owner_user_id_fkey
FOREIGN KEY (owner_user_id)
REFERENCES users(id)
ON DELETE SET NULL;
