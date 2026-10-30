# Restoration regression suite: auth/portal, books, members, shelves, circulation, visits, reports, uploads, settings
import io
import os
import uuid
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
PETUGAS = {"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"}
SISWA = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin():
    return _h(_login(ADMIN)["token"])


@pytest.fixture(scope="module")
def siswa():
    return _h(_login(SISWA)["token"])


# --- Auth & portal ---
class TestAuth:
    def test_admin_login(self):
        d = _login(ADMIN)
        assert d["role"] == "admin" and isinstance(d["token"], str)

    def test_petugas_login_admin_portal(self):
        assert _login(PETUGAS)["role"] == "petugas"

    def test_siswa_rejected_admin_portal(self):
        r = requests.post(f"{API}/auth/login", json={**SISWA, "portal": "admin"})
        assert r.status_code == 403

    def test_admin_rejected_siswa_portal(self):
        r = requests.post(f"{API}/auth/login", json={**ADMIN, "portal": "siswa"})
        assert r.status_code == 403

    def test_siswa_login(self):
        assert _login(SISWA)["role"] == "siswa"

    def test_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": f"nouser_{uuid.uuid4().hex[:6]}@x.id", "password": "x", "portal": "admin"})
        assert r.status_code == 401

    def test_me(self, admin):
        r = requests.get(f"{API}/auth/me", headers=admin)
        assert r.status_code == 200 and r.json()["role"] == "admin"

    def test_dashboard(self, admin):
        r = requests.get(f"{API}/dashboard", headers=admin)
        assert r.status_code == 200 and isinstance(r.json(), dict)

    def test_siswa_can_read_books_shelves(self, siswa):
        assert requests.get(f"{API}/books", headers=siswa).status_code == 200
        assert requests.get(f"{API}/shelves", headers=siswa).status_code == 200

    def test_siswa_forbidden_members(self, siswa):
        assert requests.get(f"{API}/members", headers=siswa).status_code == 403


# --- Shelves / Books / Members / Circulation ---
class TestCrudFlow:
    def test_full_flow(self, admin):
        sid = "T" + uuid.uuid4().hex[:5].upper()
        r = requests.post(f"{API}/shelves", headers=admin, json={"id": sid, "name": "TEST_Rak", "capacity": 50, "color": "azure"})
        assert r.status_code == 200, r.text
        r = requests.put(f"{API}/shelves/{sid}", headers=admin, json={"id": sid, "name": "TEST_Rak2", "capacity": 60, "color": "azure"})
        assert r.status_code == 200 and r.json()["name"] == "TEST_Rak2"

        title = f"TEST_Buku {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/books", headers=admin, json={"title": title, "author": "TEST_Penulis", "shelf": sid, "stock": 2})
        assert r.status_code == 200, r.text
        book = r.json(); bid = book["id"]
        assert book["merged"] is False and book["stock"] == 2
        r = requests.put(f"{API}/books/{bid}", headers=admin, json={"title": title + " E", "author": "TEST_Penulis", "shelf": sid, "category": "Umum"})
        assert r.status_code == 200 and r.json()["title"] == title + " E"
        r = requests.patch(f"{API}/books/{bid}/stock", headers=admin, json={"stock": 3})
        assert r.status_code == 200 and r.json()["stock"] == 3
        assert any(b["id"] == bid for b in requests.get(f"{API}/books", headers=admin).json())

        r = requests.post(f"{API}/members", headers=admin, json={"name": "TEST_Siswa", "student_id": "T" + uuid.uuid4().hex[:6], "class_name": "X-1"})
        assert r.status_code == 200, r.text
        m = r.json(); mid = m["id"]
        assert any(x["id"] == mid for x in requests.get(f"{API}/members", headers=admin).json())

        r = requests.post(f"{API}/transactions", headers=admin, json={"member_id": mid, "book_id": bid, "action": "pinjam"})
        assert r.status_code == 200, r.text
        r = requests.post(f"{API}/transactions", headers=admin, json={"member_id": mid, "book_id": bid, "action": "pinjam"})
        assert r.status_code == 400
        r = requests.post(f"{API}/transactions", headers=admin, json={"member_id": mid, "book_id": bid, "action": "kembali"})
        assert r.status_code == 200, r.text

        # visits check-in by NIS, search by name
        r = requests.post(f"{API}/visits/scan", headers=admin, json={"code": m["student_id"]})
        assert r.status_code == 200 and r.json()["action"] == "masuk", r.text
        r = requests.get(f"{API}/visits/member-search", headers=admin, params={"q": "TEST_Siswa"})
        assert r.status_code == 200 and any(x["id"] == mid for x in r.json())
        vid = requests.get(f"{API}/visits", headers=admin).json()["items"]
        vid = [v for v in vid if v.get("member_id") == mid][0]["id"]
        assert requests.delete(f"{API}/visits/{vid}", headers=admin).status_code == 200

        # cleanup
        assert requests.delete(f"{API}/books/{bid}", headers=admin).status_code == 200
        assert requests.delete(f"{API}/members/{mid}", headers=admin).status_code == 200
        assert requests.delete(f"{API}/shelves/{sid}", headers=admin).status_code == 200


# --- Reports / exports ---
class TestReports:
    def test_reports(self, admin):
        r = requests.get(f"{API}/reports", headers=admin)
        assert r.status_code == 200 and {"transactions", "loans", "incoming", "missing"} <= set(r.json())

    @pytest.mark.parametrize("t", ["transaksi", "masuk", "hilang", "kunjungan", "statistik", "peringkat"])
    def test_pdf(self, admin, t):
        r = requests.get(f"{API}/reports/export.pdf", headers=admin, params={"type": t, "period": "semua"})
        assert r.status_code == 200 and r.content[:4] == b"%PDF", r.text[:200]

    @pytest.mark.parametrize("t", ["transaksi", "masuk", "hilang", "kunjungan", "statistik", "peringkat"])
    def test_xlsx(self, admin, t):
        r = requests.get(f"{API}/reports/export.xlsx", headers=admin, params={"type": t, "period": "semua"})
        assert r.status_code == 200 and r.content[:2] == b"PK", r.text[:200]

    def test_summary(self, admin):
        r = requests.get(f"{API}/reports/summary", headers=admin)
        assert r.status_code == 200, r.text[:200]


# --- Uploads (object storage) ---
class TestUpload:
    def test_upload_and_download(self, admin):
        buf = io.BytesIO(); Image.new("RGB", (200, 200), (10, 80, 160)).save(buf, "PNG")
        r = requests.post(f"{API}/uploads/photo", headers=admin, files={"file": ("t.png", buf.getvalue(), "image/png")}, timeout=120)
        assert r.status_code == 200, r.text
        url = r.json()["url"]
        assert url.startswith("/api/files/")
        g = requests.get(f"{BASE_URL}{url}", headers=admin, timeout=60)
        assert g.status_code == 200 and g.content[:2] == b"\xff\xd8"

    def test_invalid_file(self, admin):
        r = requests.post(f"{API}/uploads/photo", headers=admin, files={"file": ("t.png", b"notanimage", "image/png")})
        assert r.status_code == 400


# --- Settings (card design) ---
class TestSettings:
    def test_get_put_settings(self, admin):
        orig = requests.get(f"{API}/settings", headers=admin).json()
        payload = {k: orig[k] for k in orig if k not in ("member_photo_upload",) and not k.startswith("updated")}
        payload["card_theme"] = "TEST_theme"
        r = requests.put(f"{API}/settings", headers=admin, json=payload)
        assert r.status_code == 200 and r.json()["card_theme"] == "TEST_theme"
        assert requests.get(f"{API}/settings", headers=admin).json()["card_theme"] == "TEST_theme"
        payload["card_theme"] = orig["card_theme"]
        assert requests.put(f"{API}/settings", headers=admin, json=payload).status_code == 200

    def test_siswa_cannot_put_settings(self, siswa):
        assert requests.put(f"{API}/settings", headers=siswa, json={}).status_code == 403
