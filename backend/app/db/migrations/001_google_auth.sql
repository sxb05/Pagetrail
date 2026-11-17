-- Google accounts share the users table with password accounts.
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_unique ON users (email);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub_unique ON users (google_sub);
