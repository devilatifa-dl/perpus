# Auth Testing Playbook

Demo accounts are seeded by the backend. Login with the credentials in `/app/memory/test_credentials.md`.

Endpoints: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`.

Expected behavior: successful login sets an httpOnly `access_token` cookie; `/api/auth/me` returns the role and profile; invalid credentials return HTTP 401.