# Key Rotation Guide

Last Updated: 2026-03-17
Scope: ENCRYPTION_MASTER_KEY, ENCRYPTION_FALLBACK_KEYS, JWT_SECRET

## Goal

Rotate signing and encryption secrets without breaking existing encrypted integration tokens or OAuth state validation.

## Supported Secret Sources

1. Direct environment variable.
2. File indirection via \*\_FILE variables.

Examples:

```dotenv
JWT_SECRET_FILE=/run/secrets/jwt_secret
ENCRYPTION_MASTER_KEY_FILE=/run/secrets/encryption_master_key
ENCRYPTION_FALLBACK_KEYS_FILE=/run/secrets/encryption_fallback_keys
```

## Rotation Procedure

1. Generate new key material in secret manager.
2. Set new key as ENCRYPTION_MASTER_KEY.
3. Move previous ENCRYPTION_MASTER_KEY into ENCRYPTION_FALLBACK_KEYS (comma-separated).
4. Deploy all services.
5. Run token re-encryption job (optional but recommended) so old ciphertext is rewritten with current primary key.
6. After migration window, remove deprecated fallback keys.

## JWT Secret Rotation

1. Update JWT_SECRET in secret manager.
2. Keep old JWT secret in a temporary compatibility layer only if you validate legacy tokens outside this service.
3. Force refresh/logout for stale sessions if strict cutover is required.

## Operational Checks

1. Verify OAuth callback endpoints continue to validate state signatures.
2. Verify integration account token upsert still succeeds.
3. Watch logs for missing required secret errors.

## Rollback

1. Restore previous ENCRYPTION_MASTER_KEY and JWT_SECRET values.
2. Re-deploy service.
3. Confirm callback and integration flows recover.
