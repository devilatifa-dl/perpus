"""Backend tests for login bug fix (Jan 2026 iteration 17).

Covers:
- admin/petugas/siswa login success and portal gating (403)
- wrong password Indonesian message (uses only 1-2 attempts per account to avoid lockout)
- POST /api/auth/login returns user + token field
- GET /api/auth/me works with Bearer header alone AND with cookie alone
- CORS preflight from https://perpusmansa.vercel.app allowed with credentials
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # fallback to frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1].rstrip("/")

ADMIN = ("admin@smansa.sch.id", "admin123")
PETUGAS = ("petugas@smansa.sch.id", "petugas123")
SISWA = ("siswa@smansa.sch.id", "siswa123")


def _login(email, password, portal="admin", session=None):
    s = session or requests.Session()
    return s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password, "portal": portal}, timeout=15)


# --- Login success for all 3 roles ---
def test_admin_login_success():
    r = _login(*ADMIN, portal="admin")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("email") == ADMIN[0]
    assert data.get("role") == "admin"
    assert isinstance(data.get("token"), str) and len(data["token"]) > 20
    assert "password_hash" not in data
    # cookie set
    assert "access_token" in r.cookies


def test_petugas_login_success():
    r = _login(*PETUGAS, portal="admin")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "petugas"
    assert "token" in data


def test_siswa_login_success():
    r = _login(*SISWA, portal="siswa")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "siswa"
    assert "token" in data


# --- Portal gating (403) ---
def test_siswa_cannot_login_at_admin_portal():
    r = _login(*SISWA, portal="admin")
    assert r.status_code == 403
    assert "siswa" in r.json().get("detail", "").lower()


def test_admin_cannot_login_at_siswa_portal():
    r = _login(*ADMIN, portal="siswa")
    assert r.status_code == 403


# --- Wrong password: Indonesian error, uses only 1 attempt ---
def test_wrong_password_indonesian_error():
    # Use a dummy email to avoid consuming attempts on real accounts
    r = _login("nonexistent-xyz@smansa.sch.id", "wrongpw", portal="admin")
    assert r.status_code == 401
    assert "sandi" in r.json().get("detail", "").lower() or "email" in r.json().get("detail", "").lower()


# --- /auth/me with Bearer header alone (no cookies) ---
def test_me_with_bearer_only():
    r = _login(*ADMIN, portal="admin")
    assert r.status_code == 200
    token = r.json()["token"]
    # use a fresh session so no cookies
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    assert r2.status_code == 200, r2.text
    assert r2.json()["email"] == ADMIN[0]


# --- /auth/me with cookie alone (no Authorization header) ---
def test_me_with_cookie_only():
    s = requests.Session()
    r = _login(*ADMIN, portal="admin", session=s)
    assert r.status_code == 200
    # Session now has access_token cookie; no Authorization header set
    r2 = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r2.status_code == 200, r2.text
    assert r2.json()["email"] == ADMIN[0]


# --- CORS preflight from vercel.app ---
def test_cors_preflight_vercel():
    r = requests.options(
        f"{BASE_URL}/api/auth/login",
        headers={
            "Origin": "https://perpusmansa.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=10,
    )
    assert r.status_code in (200, 204), r.text
    assert r.headers.get("access-control-allow-origin") == "https://perpusmansa.vercel.app"
    assert r.headers.get("access-control-allow-credentials", "").lower() == "true"


# --- Logout clears cookie ---
def test_logout_clears_cookie():
    s = requests.Session()
    _login(*ADMIN, portal="admin", session=s)
    r = s.post(f"{BASE_URL}/api/auth/logout", timeout=10)
    assert r.status_code == 200
    # subsequent /me (cookie-only) should 401
    s.headers.pop("Authorization", None)
    r2 = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert r2.status_code == 401
