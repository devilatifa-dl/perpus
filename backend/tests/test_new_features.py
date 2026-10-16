"""Backend tests for new features: reports/summary, photo-upload toggle, uploads, member accounts, member photo."""
import io, os, pytest, requests
from PIL import Image
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = BASE_URL + "/api"


def login(session, email, password, portal="admin"):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password, "portal": portal})
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r


@pytest.fixture
def admin():
    s = requests.Session()
    login(s, "admin@smansa.sch.id", "admin123", "admin")
    yield s


@pytest.fixture
def siswa_shared():
    s = requests.Session()
    login(s, "siswa@smansa.sch.id", "siswa123", "siswa")
    yield s


@pytest.fixture
def siti():
    s = requests.Session()
    login(s, "siti@smansa.sch.id", "siti123", "siswa")
    yield s


def make_image(size=(2000, 1500), fmt="JPEG"):
    img = Image.new("RGB", size, (120, 60, 200))
    for x in range(0, size[0], 50):
        for y in range(0, size[1], 50):
            img.putpixel((x, y), (255, 255, 0))
    buf = io.BytesIO()
    img.save(buf, fmt, quality=95)
    return buf.getvalue()


# ---------- Reports / Summary ----------
class TestReportsSummary:
    def test_default(self, admin):
        r = admin.get(f"{API}/reports/summary")
        assert r.status_code == 200
        d = r.json()
        for k in ("kpis", "totals", "series", "top_books", "top_members", "start", "end", "group"):
            assert k in d
        for k in ("books", "titles", "members", "active_loans", "overdue", "visits_today"):
            assert k in d["kpis"], f"missing kpi {k}"
        assert d["group"] == "day"
        assert isinstance(d["series"], list)

    def test_range_and_month(self, admin):
        r = admin.get(f"{API}/reports/summary", params={"start": "2025-01-01", "end": "2025-12-31", "group": "month"})
        assert r.status_code == 200
        d = r.json()
        assert d["group"] == "month"
        assert len(d["series"]) == 12

    def test_invalid_date(self, admin):
        r = admin.get(f"{API}/reports/summary", params={"start": "not-a-date"})
        assert r.status_code == 400

    def test_invalid_group(self, admin):
        r = admin.get(f"{API}/reports/summary", params={"group": "year"})
        assert r.status_code == 400

    def test_siswa_forbidden(self, siswa_shared):
        r = siswa_shared.get(f"{API}/reports/summary")
        assert r.status_code == 403


# ---------- Photo-upload toggle ----------
class TestPhotoUploadToggle:
    def test_toggle_and_persist(self, admin):
        r = admin.put(f"{API}/settings/photo-upload", json={"enabled": False})
        assert r.status_code == 200
        assert r.json()["member_photo_upload"] is False
        r2 = admin.get(f"{API}/settings")
        assert r2.json()["member_photo_upload"] is False
        # restore ON
        r3 = admin.put(f"{API}/settings/photo-upload", json={"enabled": True})
        assert r3.status_code == 200
        assert r3.json()["member_photo_upload"] is True

    def test_siswa_cannot_toggle(self, siswa_shared):
        r = siswa_shared.put(f"{API}/settings/photo-upload", json={"enabled": False})
        assert r.status_code == 403


# ---------- Uploads / Files ----------
class TestUploads:
    def test_upload_resize_and_private(self, admin):
        img = make_image((2400, 1800))
        assert len(img) > 100_000
        r = admin.post(f"{API}/uploads/photo", files={"file": ("big.jpg", img, "image/jpeg")})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["url"].startswith("/api/files/")
        assert max(data["width"], data["height"]) <= 1080
        assert data["size"] <= 600 * 1024  # ~<500KB target
        # Need auth to view
        anon = requests.get(BASE_URL + data["url"])
        assert anon.status_code == 401
        # With auth works
        auth = admin.get(BASE_URL + data["url"])
        assert auth.status_code == 200
        assert auth.headers["content-type"].startswith("image/")

    def test_upload_png_rgba(self, admin):
        buf = io.BytesIO()
        Image.new("RGBA", (1200, 800), (255, 0, 0, 128)).save(buf, "PNG")
        r = admin.post(f"{API}/uploads/photo", files={"file": ("x.png", buf.getvalue(), "image/png")})
        assert r.status_code == 200
        assert max(r.json()["width"], r.json()["height"]) <= 1080

    def test_siswa_rejected_when_off(self, admin, siswa_shared):
        # turn off
        admin.put(f"{API}/settings/photo-upload", json={"enabled": False})
        try:
            img = make_image((800, 600))
            r = siswa_shared.post(f"{API}/uploads/photo", files={"file": ("f.jpg", img, "image/jpeg")})
            assert r.status_code == 403
            assert "ditutup" in r.text.lower()
            # Admin still can upload
            r2 = admin.post(f"{API}/uploads/photo", files={"file": ("f.jpg", img, "image/jpeg")})
            assert r2.status_code == 200
        finally:
            admin.put(f"{API}/settings/photo-upload", json={"enabled": True})

    def test_siswa_allowed_when_on(self, admin, siswa_shared):
        admin.put(f"{API}/settings/photo-upload", json={"enabled": True})
        img = make_image((800, 600))
        r = siswa_shared.post(f"{API}/uploads/photo", files={"file": ("f.jpg", img, "image/jpeg")})
        assert r.status_code == 200

    def test_invalid_file(self, admin):
        r = admin.post(f"{API}/uploads/photo", files={"file": ("x.txt", b"not an image", "text/plain")})
        assert r.status_code == 400


# ---------- Member Accounts ----------
class TestMemberAccount:
    def test_create_update_delete_account(self, admin):
        # pick a member without account; try MB-2024001 (shared), create temp member
        payload = {"name": "TEST_Zeta User", "class_name": "XII-TEST", "student_id": "99999"}
        r = admin.post(f"{API}/members", json=payload)
        assert r.status_code in (200, 201), r.text
        mid = r.json()["id"]
        try:
            # create account
            r = admin.put(f"{API}/members/{mid}/account", json={"email": "test_zeta@smansa.sch.id", "password": "zeta123"})
            assert r.status_code == 200, r.text
            # duplicate email with admin's email
            r2 = admin.put(f"{API}/members/{mid}/account", json={"email": "admin@smansa.sch.id", "password": "zeta123"})
            assert r2.status_code == 400
            # Get account
            r3 = admin.get(f"{API}/members/{mid}/account")
            assert r3.status_code == 200 and r3.json()["email"] == "test_zeta@smansa.sch.id"
            # Login with new acc
            s = requests.Session()
            lr = s.post(f"{API}/auth/login", json={"email": "test_zeta@smansa.sch.id", "password": "zeta123", "portal": "siswa"})
            assert lr.status_code == 200
            # Delete
            dr = admin.delete(f"{API}/members/{mid}/account")
            assert dr.status_code == 200
            dr2 = admin.delete(f"{API}/members/{mid}/account")
            assert dr2.status_code == 404
        finally:
            admin.delete(f"{API}/members/{mid}")

    def test_short_password(self, admin):
        # just ensure validation
        payload = {"name": "TEST_Alpha", "class_name": "XII-TEST", "student_id": "99998"}
        mr = admin.post(f"{API}/members", json=payload)
        mid = mr.json()["id"]
        try:
            r = admin.put(f"{API}/members/{mid}/account", json={"email": "test_alpha@smansa.sch.id", "password": "abc"})
            assert r.status_code == 400
        finally:
            admin.delete(f"{API}/members/{mid}")


# ---------- Member photo (ACL) ----------
class TestMemberPhoto:
    def test_linked_cannot_change_other(self, siti):
        # Siti is MB-2024002, try to patch MB-2024001
        r = siti.post(f"{API}/members/MB-2024001/photo", json={"photo": "/api/files/foo"})
        assert r.status_code == 403

    def test_photo_must_be_uploaded_url(self, siti, admin):
        admin.put(f"{API}/settings/photo-upload", json={"enabled": True})
        r = siti.post(f"{API}/members/MB-2024002/photo", json={"photo": "https://evil.example.com/x.jpg"})
        assert r.status_code == 400

    def test_siswa_blocked_when_toggle_off(self, siti, admin):
        admin.put(f"{API}/settings/photo-upload", json={"enabled": False})
        try:
            r = siti.post(f"{API}/members/MB-2024002/photo", json={"photo": "/api/files/foo"})
            assert r.status_code == 403
        finally:
            admin.put(f"{API}/settings/photo-upload", json={"enabled": True})


# ---------- Auth negative ----------
class TestAuth:
    def test_me_without_cookie(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_bad_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": "admin@smansa.sch.id", "password": "wrong", "portal": "admin"})
        assert r.status_code == 401
