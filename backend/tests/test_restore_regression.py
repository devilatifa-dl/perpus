# Restore regression tests: auth/roles, dashboard, books+cover, members+photo, shelves, sirkulasi, visits, reports, backup
import io, os, base64, zipfile, pytest, requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def login(email, pw, portal):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": pw, "portal": portal}, timeout=30)


@pytest.fixture(scope="module")
def admin():
    r = login("admin@smansa.sch.id", "admin123", "admin")
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code} {r.text}")
    s = requests.Session(); s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s


@pytest.fixture(scope="module")
def siswa():
    r = login("siswa@smansa.sch.id", "siswa123", "siswa")
    if r.status_code != 200:
        pytest.skip(f"siswa login failed {r.status_code} {r.text}")
    s = requests.Session(); s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s


@pytest.fixture(scope="module")
def created():
    d = {"books": [], "members": [], "shelves": [], "visits": []}
    yield d
    r = login("admin@smansa.sch.id", "admin123", "admin")
    s = requests.Session(); s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    for v in d["visits"]: s.delete(f"{API}/visits/{v}")
    for b in d["books"]: s.delete(f"{API}/books/{b}")
    for m in d["members"]: s.delete(f"{API}/members/{m}")
    for sh in d["shelves"]: s.delete(f"{API}/shelves/{sh}")


def png_bytes(color=(200, 30, 30), size=(120, 160)):
    buf = io.BytesIO(); Image.new("RGB", size, color).save(buf, "PNG"); return buf.getvalue()


# --- Auth & roles
class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/"); assert r.status_code == 200 and "aktif" in r.json()["message"]

    def test_admin_petugas_login(self):
        for e, p, role in [("admin@smansa.sch.id", "admin123", "admin"), ("petugas@smansa.sch.id", "petugas123", "petugas")]:
            r = login(e, p, "admin"); assert r.status_code == 200, r.text
            assert r.json()["role"] == role and r.json()["token"] and "password_hash" not in r.json()

    def test_siswa_login_portal_rules(self):
        assert login("siswa@smansa.sch.id", "siswa123", "siswa").status_code == 200
        assert login("siswa@smansa.sch.id", "siswa123", "admin").status_code == 403
        assert login("admin@smansa.sch.id", "admin123", "siswa").status_code == 403

    def test_me(self, admin):
        r = admin.get(f"{API}/auth/me"); assert r.status_code == 200 and r.json()["email"] == "admin@smansa.sch.id"

    def test_siswa_forbidden(self, siswa):
        for p in ["/members", "/reports", "/reports/export.pdf", "/reports/summary", "/transactions", "/admin/backup.zip"]:
            assert siswa.get(f"{API}{p}").status_code == 403, p

    def test_siswa_allowed(self, siswa):
        for p in ["/books", "/shelves", "/visits/leaderboard", "/loans/leaderboard", "/dashboard"]:
            assert siswa.get(f"{API}{p}").status_code == 200, p
        lb = siswa.get(f"{API}/visits/leaderboard").json()
        assert all("minutes" not in s for s in lb.get("students", []))


# --- Dashboard, books, cover
class TestBooks:
    def test_dashboard(self, admin):
        d = admin.get(f"{API}/dashboard").json()
        for k in ["books", "titles", "available", "members", "borrowed", "visitors_today", "overdue"]:
            assert k in d and isinstance(d[k], int)

    def test_book_crud_and_cover(self, admin, created):
        cover = "data:image/png;base64," + base64.b64encode(png_bytes()).decode()
        r = admin.post(f"{API}/books", json={"title": "TEST_Buku Regresi", "author": "TEST_Penulis", "category": "Umum", "shelf": "R-01", "cover": cover, "stock": 2})
        assert r.status_code == 200, r.text
        b = r.json(); created["books"].append(b["id"])
        assert b["stock"] == 2 and b["available"] == 2 and b["cover"].startswith(f"/api/books/{b['id']}/cover")
        c = requests.get(f"{BASE_URL}{b['cover']}"); assert c.status_code == 200 and c.headers["content-type"] == "image/jpeg"
        full = requests.get(f"{API}/books/{b['id']}/cover?s=full"); assert full.status_code == 200
        lst = admin.get(f"{API}/books").json(); assert any(x["id"] == b["id"] for x in lst)
        u = admin.put(f"{API}/books/{b['id']}", json={"title": "TEST_Buku Regresi Edit", "author": "TEST_Penulis", "category": "Sains", "shelf": "R-01", "isbn": "", "cover": b["cover"]})
        assert u.status_code == 200 and u.json()["title"] == "TEST_Buku Regresi Edit"
        # cover preserved when cover ref passed back
        assert requests.get(f"{API}/books/{b['id']}/cover").status_code == 200


# --- Members & photo storage in Mongo
class TestMembers:
    def test_member_and_photo(self, admin, created):
        r = admin.post(f"{API}/members", json={"name": "TEST_Siswa Regresi", "student_id": "TEST99881", "class_name": "X TEST"})
        assert r.status_code == 200, r.text
        m = r.json(); created["members"].append(m["id"])
        assert admin.post(f"{API}/members", json={"name": "dup", "student_id": "TEST99881", "class_name": "X"}).status_code == 400
        up = admin.post(f"{API}/uploads/photo", files={"file": ("a.png", png_bytes(), "image/png")})
        assert up.status_code == 200, up.text
        url = up.json()["url"]; assert url.startswith("/api/files/")
        f = admin.get(f"{BASE_URL}{url}"); assert f.status_code == 200 and f.content[:2] == b"\xff\xd8"
        assert requests.get(f"{BASE_URL}{url}").status_code == 401
        p = admin.post(f"{API}/members/{m['id']}/photo", json={"photo": url}); assert p.status_code == 200 and p.json()["photo"] == url
        assert admin.post(f"{API}/uploads/photo", files={"file": ("x.txt", b"notimage", "text/plain")}).status_code == 400
        assert any(x["id"] == m["id"] for x in admin.get(f"{API}/members").json())


# --- Shelves
class TestShelves:
    def test_shelf_crud(self, admin, created):
        r = admin.post(f"{API}/shelves", json={"id": "TST-9", "name": "TEST_Rak", "capacity": 10, "color": "mint"})
        assert r.status_code == 200, r.text; created["shelves"].append("TST-9")
        u = admin.put(f"{API}/shelves/TST-9", json={"id": "TST-9", "name": "TEST_Rak2", "capacity": 20, "color": "mint"})
        assert u.status_code == 200 and u.json()["capacity"] == 20
        assert any(s["id"] == "TST-9" for s in admin.get(f"{API}/shelves").json())
        assert admin.delete(f"{API}/shelves/TST-9").status_code == 200; created["shelves"].remove("TST-9")


# --- Sirkulasi + visits (depends on created book/member)
class TestFlows:
    def test_borrow_return(self, admin, created):
        if not created["books"] or not created["members"]: pytest.skip("deps")
        b, m = created["books"][0], created["members"][0]
        p = admin.post(f"{API}/transactions", json={"member_id": m, "book_id": b, "action": "pinjam"}); assert p.status_code == 200, p.text
        assert admin.post(f"{API}/transactions", json={"member_id": m, "book_id": b, "action": "pinjam"}).status_code == 400
        bk = next(x for x in admin.get(f"{API}/books").json() if x["id"] == b); assert bk["borrowed"] == 1
        k = admin.post(f"{API}/transactions", json={"member_id": m, "book_id": b, "action": "kembali"}); assert k.status_code == 200
        bk = next(x for x in admin.get(f"{API}/books").json() if x["id"] == b); assert bk["borrowed"] == 0
        h = admin.get(f"{API}/members/{m}/history").json(); assert h["total"] == 1 and h["active"] == 0

    def test_visit_scan(self, admin, created):
        r = admin.post(f"{API}/visits/scan", json={"code": "TEST99881"}); assert r.status_code == 200, r.text
        assert r.json()["action"] in ("masuk", "sudah_masuk"); created["visits"].append(r.json()["visit"]["id"])
        r2 = admin.post(f"{API}/visits/scan", json={"code": "TEST99881"}); assert r2.json()["action"] == "sudah_masuk"
        assert admin.post(f"{API}/visits/scan", json={"code": "NOPE-XYZ"}).status_code == 404
        vid = r.json()["visit"]["id"]
        co = admin.post(f"{API}/visits/{vid}/checkout"); assert co.status_code == 200 and co.json()["check_out"]
        v = admin.get(f"{API}/visits").json(); assert any(x["id"] == vid for x in v["items"])


# --- Reports & backup
class TestReports:
    def test_reports_json(self, admin):
        r = admin.get(f"{API}/reports"); assert r.status_code == 200 and "loans" in r.json()
        s = admin.get(f"{API}/reports/summary"); assert s.status_code == 200
        assert admin.get(f"{API}/loans/leaderboard").status_code == 200
        assert admin.get(f"{API}/visits/stats").status_code == 200

    @pytest.mark.parametrize("t", ["transaksi", "masuk", "hilang", "kunjungan", "statistik", "peringkat", "peringkat-pinjam"])
    def test_exports(self, admin, t):
        p = admin.get(f"{API}/reports/export.pdf", params={"type": t, "period": "semua"}, timeout=60)
        assert p.status_code == 200 and p.content[:4] == b"%PDF", f"{t} pdf {p.status_code} {p.text[:200]}"
        x = admin.get(f"{API}/reports/export.xlsx", params={"type": t, "period": "semua"}, timeout=60)
        assert x.status_code == 200 and x.content[:2] == b"PK", f"{t} xlsx {x.status_code}"

    def test_summary_exports(self, admin):
        assert admin.get(f"{API}/reports/summary.pdf", timeout=60).content[:4] == b"%PDF"
        assert admin.get(f"{API}/reports/summary.xlsx", timeout=60).content[:2] == b"PK"

    def test_backup_zip(self, admin):
        r = admin.get(f"{API}/admin/backup.zip", timeout=120); assert r.status_code == 200
        z = zipfile.ZipFile(io.BytesIO(r.content)); names = z.namelist()
        assert "data-cadangan.json" in names and "BACA-SAYA.txt" in names

    def test_backup_petugas_forbidden(self):
        r = login("petugas@smansa.sch.id", "petugas123", "admin")
        assert requests.get(f"{API}/admin/backup.zip", headers={"Authorization": f"Bearer {r.json()['token']}"}).status_code == 403
