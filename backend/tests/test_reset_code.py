"""Tests for admin reset-data verification code feature.

Covers:
- Permission gating (petugas 403)
- Rate-limit (60s) on /api/admin/reset-code
- /api/admin/reset-data: missing/wrong code -> 400 (no deletion)
- After 5 wrong attempts code is invalidated
- Success path: direct Mongo seed with bcrypt("123456") -> reset succeeds + replay fails
- Backup is taken BEFORE destructive tests and restored AFTER
"""
import os
import io
import json
import pytest
import requests
import bcrypt
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # fallback: read from frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
PETUGAS = {"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"}


# ---------- helpers ----------
def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["token"]


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def petugas_token():
    return _login(PETUGAS)


@pytest.fixture(scope="module")
def backup_payload(admin_token):
    """Download JSON backup once before destructive tests."""
    r = requests.get(f"{BASE_URL}/api/admin/backup", headers=_hdr(admin_token), timeout=60)
    assert r.status_code == 200, f"backup failed {r.status_code}"
    data = r.json()
    assert "collections" in data
    print(f"[backup] took {sum(len(v) for v in data['collections'].values())} docs across {len(data['collections'])} collections")
    return data


# ---------- Permission tests ----------
class TestPermissions:
    def test_petugas_cannot_request_code(self, petugas_token):
        r = requests.post(f"{BASE_URL}/api/admin/reset-code", headers=_hdr(petugas_token), timeout=20)
        assert r.status_code == 403, r.text
        assert "admin" in r.json().get("detail", "").lower()

    def test_petugas_cannot_reset_data(self, petugas_token):
        r = requests.post(f"{BASE_URL}/api/admin/reset-data",
                          headers=_hdr(petugas_token),
                          json={"include_books": False, "code": "123456"}, timeout=20)
        assert r.status_code == 403, r.text


# ---------- Reset-data validation (no deletion must happen) ----------
class TestResetDataValidation:
    def test_no_code_in_db_returns_400(self, admin_token, mongo, backup_payload):
        # Ensure no reset code exists
        mongo.reset_codes.delete_many({})
        before = mongo.members.count_documents({})
        r = requests.post(f"{BASE_URL}/api/admin/reset-data",
                          headers=_hdr(admin_token),
                          json={"include_books": False, "code": ""}, timeout=20)
        assert r.status_code == 400, r.text
        detail = r.json().get("detail", "").lower()
        assert "kadaluarsa" in detail or "kedaluwarsa" in detail or "tidak ada" in detail
        after = mongo.members.count_documents({})
        assert after == before, "No deletion should happen on missing code"

    def test_wrong_code_returns_400_and_no_deletion(self, admin_token, mongo):
        # Seed a valid code so attempts counter can increment
        code_hash = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
        mongo.reset_codes.update_one(
            {"id": "reset"},
            {"$set": {
                "id": "reset",
                "code_hash": code_hash,
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                "sent_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
                "attempts": 0,
            }},
            upsert=True,
        )
        before = mongo.members.count_documents({})
        r = requests.post(f"{BASE_URL}/api/admin/reset-data",
                          headers=_hdr(admin_token),
                          json={"include_books": False, "code": "000000"}, timeout=20)
        assert r.status_code == 400, r.text
        assert "salah" in r.json().get("detail", "").lower()
        after = mongo.members.count_documents({})
        assert after == before
        rec = mongo.reset_codes.find_one({"id": "reset"})
        assert rec["attempts"] == 1

    def test_five_wrong_attempts_invalidate_code(self, admin_token, mongo):
        # ensure a fresh code with attempts=0
        code_hash = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
        mongo.reset_codes.update_one(
            {"id": "reset"},
            {"$set": {
                "id": "reset",
                "code_hash": code_hash,
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                "sent_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
                "attempts": 0,
            }},
            upsert=True,
        )
        # 5 wrong attempts -> all 400
        for i in range(5):
            r = requests.post(f"{BASE_URL}/api/admin/reset-data",
                              headers=_hdr(admin_token),
                              json={"include_books": False, "code": "999999"}, timeout=20)
            assert r.status_code == 400, f"attempt {i}: {r.text}"
        # 6th attempt (even with correct code) should fail because code was deleted
        r = requests.post(f"{BASE_URL}/api/admin/reset-data",
                          headers=_hdr(admin_token),
                          json={"include_books": False, "code": "123456"}, timeout=20)
        assert r.status_code == 400, r.text
        detail = r.json().get("detail", "").lower()
        # could be "terlalu banyak" or "tidak ada / kedaluwarsa" depending on which path hit
        assert any(k in detail for k in ("terlalu banyak", "tidak ada", "kedaluwarsa", "kadaluarsa"))
        rec = mongo.reset_codes.find_one({"id": "reset"})
        assert rec is None, "Code should be deleted after invalidation"


# ---------- Success path ----------
class TestResetSuccess:
    def test_reset_with_valid_code_succeeds_and_replay_fails(self, admin_token, mongo, backup_payload):
        # Seed valid code "123456"
        code_hash = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
        mongo.reset_codes.update_one(
            {"id": "reset"},
            {"$set": {
                "id": "reset",
                "code_hash": code_hash,
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                "sent_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
                "attempts": 0,
            }},
            upsert=True,
        )
        r = requests.post(f"{BASE_URL}/api/admin/reset-data",
                          headers=_hdr(admin_token),
                          json={"include_books": False, "code": "123456"}, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert "deleted" in body
        # members should be 0 now
        assert mongo.members.count_documents({}) == 0
        # Books should NOT be deleted (include_books False)
        # (don't assert >0 because preview may be empty, just assert key presence)
        assert body["deleted"].get("books", 0) == 0
        # Replay: same code must now fail (code deleted)
        r2 = requests.post(f"{BASE_URL}/api/admin/reset-data",
                           headers=_hdr(admin_token),
                           json={"include_books": False, "code": "123456"}, timeout=20)
        assert r2.status_code == 400, r2.text

    def test_zz_restore_backup(self, admin_token, backup_payload, mongo):
        """Named 'zz' to run LAST within class - restores preview data."""
        payload_bytes = json.dumps(backup_payload).encode("utf-8")
        files = {"file": ("backup.json", io.BytesIO(payload_bytes), "application/json")}
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.post(f"{BASE_URL}/api/admin/restore", headers=headers, files=files, timeout=120)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert "restored" in body
        # Verify members restored to pre-reset count
        expected_members = len(backup_payload["collections"].get("members", []))
        actual_members = mongo.members.count_documents({})
        assert actual_members == expected_members, f"expected {expected_members} members, got {actual_members}"
        print(f"[restore] restored {sum(body['restored'].values())} docs")


# ---------- Rate-limit (real email send) ----------
class TestRateLimit:
    """Runs LAST (alphabetical after other test files) - fires one real email."""

    def test_rate_limit_60s(self, admin_token, mongo):
        # Clear any existing code so first call succeeds
        mongo.reset_codes.delete_many({})
        r1 = requests.post(f"{BASE_URL}/api/admin/reset-code", headers=_hdr(admin_token), timeout=30)
        assert r1.status_code == 200, r1.text
        body = r1.json()
        assert body.get("ok") is True
        sent_to = body.get("sent_to", "")
        # Masked email like "lat********@gmail.com" (first 3 chars + stars + @gmail.com)
        assert sent_to.startswith("lat") and sent_to.endswith("@gmail.com"), f"unexpected sent_to={sent_to}"
        assert "*" in sent_to

        # Immediate second call -> 429
        r2 = requests.post(f"{BASE_URL}/api/admin/reset-code", headers=_hdr(admin_token), timeout=20)
        assert r2.status_code == 429, r2.text
        assert "menit" in r2.json().get("detail", "").lower()

        # Cleanup: delete reset code so the user is not blocked afterwards
        mongo.reset_codes.delete_many({})
