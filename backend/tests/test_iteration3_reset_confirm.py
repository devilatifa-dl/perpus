# Iteration 3: reset-data requires admin password; login regression
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


def login(email, pw, portal):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw, "portal": portal}, timeout=20)
    return r


def token_of(r):
    d = r.json()
    return d.get("token") or d.get("access_token")


@pytest.fixture(scope="module")
def admin_h():
    r = login("admin@smansa.sch.id", "admin123", "admin")
    if r.status_code != 200:
        pytest.skip("admin login failed")
    return {"Authorization": f"Bearer {token_of(r)}"}


@pytest.fixture(scope="module")
def petugas_h():
    r = login("petugas@smansa.sch.id", "petugas123", "admin")
    if r.status_code != 200:
        pytest.skip("petugas login failed")
    return {"Authorization": f"Bearer {token_of(r)}"}


def members_count(h):
    r = requests.get(f"{BASE_URL}/api/members", headers=h, timeout=20)
    assert r.status_code == 200
    d = r.json()
    return len(d) if isinstance(d, list) else d.get("total", len(d.get("items", [])))


# Login regression
class TestLogin:
    def test_admin(self):
        r = login("admin@smansa.sch.id", "admin123", "admin")
        assert r.status_code == 200 and token_of(r)

    def test_petugas(self):
        r = login("petugas@smansa.sch.id", "petugas123", "admin")
        assert r.status_code == 200 and token_of(r)

    def test_siswa(self):
        r = login("siswa@smansa.sch.id", "siswa123", "siswa")
        assert r.status_code == 200 and token_of(r)


# Reset-data password guard
class TestResetGuard:
    def test_no_password_400(self, admin_h):
        before = members_count(admin_h)
        r = requests.post(f"{BASE_URL}/api/admin/reset-data", json={"include_books": False}, headers=admin_h, timeout=20)
        assert r.status_code == 400
        assert "Sandi admin salah" in r.json()["detail"]
        assert members_count(admin_h) == before

    def test_empty_password_400(self, admin_h):
        r = requests.post(f"{BASE_URL}/api/admin/reset-data", json={"password": ""}, headers=admin_h, timeout=20)
        assert r.status_code == 400

    def test_wrong_password_400(self, admin_h):
        before = members_count(admin_h)
        r = requests.post(f"{BASE_URL}/api/admin/reset-data", json={"include_books": True, "password": "wrongpass"}, headers=admin_h, timeout=20)
        assert r.status_code == 400
        assert r.json()["detail"] == "Sandi admin salah. Data tidak direset."
        assert members_count(admin_h) == before
        assert before > 0

    def test_petugas_403(self, petugas_h):
        r = requests.post(f"{BASE_URL}/api/admin/reset-data", json={"password": "petugas123"}, headers=petugas_h, timeout=20)
        assert r.status_code == 403

    def test_unauth(self):
        r = requests.post(f"{BASE_URL}/api/admin/reset-data", json={"password": "admin123"}, timeout=20)
        assert r.status_code in (401, 403)
