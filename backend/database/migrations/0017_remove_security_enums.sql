-- Remove remaining security/auth ENUM types so identity values remain configurable strings.
ALTER TABLE auth_login_throttles MODIFY COLUMN user_type VARCHAR(30) NOT NULL;
ALTER TABLE password_reset_tokens MODIFY COLUMN user_type VARCHAR(30) NOT NULL;
ALTER TABLE mfa_factors MODIFY COLUMN user_type VARCHAR(30) NOT NULL, MODIFY COLUMN factor_type VARCHAR(40) NOT NULL DEFAULT 'totp';
ALTER TABLE mfa_challenges MODIFY COLUMN user_type VARCHAR(30) NOT NULL;
