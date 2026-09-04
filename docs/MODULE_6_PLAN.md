# Module 6 — Auth & Session Management (M, ~1.2d)

> **Depends on:** M1 (users table), M2 (routers), M4 (sessions) | **Delivers:** `POST /auth/register|login`, `GET /auth/me`, JWT middleware, ownership checks for `DELETE /council/session` and `GET /council/sessions`

## File Manifest

```
backend/
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── security.py   # update: hash/verify, create_access_token, get_current_user dep, decode_token_optional
│   │   └── router.py     # POST /register (201), POST /login (200), GET /me (200)
│   └── routers/council.py # update _optional_auth to use security.get_current_user_optional
└── tests/
    ├── test_auth.py      # register→login→me, duplicate 409, bad pwd 401, expired 401
    └── test_sessions_auth.py # owner delete vs 403, list privacy
```

## Endpoint Contracts (contracts/openapi.yaml:243-325)

- `POST /auth/register` body `UserCreate` (email lowercased, password 8..128, display_name optional). 201 `AuthResponse` `{access_token: JWT, token_type: bearer, user: UserRead}` with JWT `{sub: email, uid: user.id, exp: 24h}` via `python-jose` HS256 + `SECRET_KEY`. 409 if email exists (case-insensitive unique index), 422 validation.
- `POST /auth/login` body `{email, password}`. Verify `passlib bcrypt`. 200 same shape. 401 bad creds.
- `GET /auth/me` header `Authorization: Bearer <jwt>` required. 200 `UserRead`. 401 if missing/invalid/expired.
- Session ties: `POST /council/query` now reads `get_current_user_optional` — if JWT valid, `user_id = user.id` else `NULL`. Already in council.py but stubbed; will replace.
- `DELETE /council/session/{id}` 403 if `sess.user_id != current_user.id` when session owned; anon (NULL) deletable by anyone (Phase 1 privacy trade-off, as per M4).
- `GET /council/sessions?user_id=&limit&offset` already filters by caller; will enforce: if `user_id` filter mismatches caller → 403.

## Security Details

- `passlib.context.CryptContext(schemes=["bcrypt"])` 12 rounds.
- `SECRET_KEY` 32+ enforced via `config.py`.
- `create_access_token(data, expires_delta=24h)` → `jwt.encode`.
- Dependency `get_current_user(token=Header Bearer)` → raises 401. `get_current_user_optional` returns `User | None`.
- Password never returned.

## Tests

- `test_register_login_me_flow` — register → token → /me 200 → login same → token.
- `test_register_duplicate_409` — same email lower/upper → 409.
- `test_login_bad_401` — wrong pwd → 401.
- `test_me_no_token_401`
- `test_delete_owner_vs_403` — userA creates session, userB delete → 403, owner → 204, anon → 204.
- `test_list_privacy` — anon cannot list someone else's via `?user_id=`.

## Approval Request

Approve this auth plan? Next: write `app/auth/security.py` (full) + `app/auth/router.py`, wire into `app/main.py`, update `council.py` optional auth, write tests.
