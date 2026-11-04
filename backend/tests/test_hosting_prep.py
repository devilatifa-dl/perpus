# Hosting-prep regression: env-driven CORS, reservation flow (siswa -> staff queue), static config checks
import os, json, re, pathlib
import pytest, requests, yaml

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ROOT = pathlib.Path("/app")


def tok(email, pw, portal):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw, "portal": portal})
    assert r.status_code == 200, r.text
    s = requests.Session(); s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s


# --- CORS (preview .env CORS_ORIGINS="*" => regex .* with credentials)
class TestCors:
    @pytest.mark.parametrize("origin", ["https://perpusmansa.vercel.app", "http://localhost:3000", "https://random.example.org"])
    def test_preflight_any_origin(self, origin):
        r = requests.options(f"{API}/auth/login", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,authorization"})
        assert r.status_code == 200, r.text
        assert r.headers.get("access-control-allow-origin") == origin
        assert r.headers.get("access-control-allow-credentials") == "true"

    def test_simple_get_echo_origin_and_expose(self):
        r = requests.get(f"{API}/", headers={"Origin": "https://x.onrender.com"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "https://x.onrender.com"
        assert "content-disposition" in r.headers.get("access-control-expose-headers", "").lower()


# --- Reservation: siswa Pesan buku -> appears in staff queue -> tolak
class TestReservation:
    def test_reserve_flow(self):
        admin = tok("admin@smansa.sch.id", "admin123", "admin")
        siswa = tok("siswa@smansa.sch.id", "siswa123", "siswa")
        b = admin.post(f"{API}/books", json={"title": "TEST_Pesan Buku", "author": "TEST", "category": "Umum", "shelf": "R-01", "stock": 1})
        assert b.status_code == 200, b.text
        bid = b.json()["id"]
        try:
            r = siswa.post(f"{API}/reservations", json={"book_id": bid})
            assert r.status_code == 200, r.text
            res = r.json(); assert res["status"] == "Menunggu" and res["book_id"] == bid
            mine = siswa.get(f"{API}/reservations/mine").json()
            assert any(x["id"] == res["id"] for x in mine)
            q = admin.get(f"{API}/reservations").json()
            assert any(x["id"] == res["id"] and x["status"] == "Menunggu" for x in q)
            p = admin.post(f"{API}/reservations/{res['id']}/process", json={"action": "tolak"})
            assert p.status_code == 200 and p.json()["status"] == "Ditolak"
        finally:
            admin.delete(f"{API}/books/{bid}")


# --- Static deploy config checks
class TestStaticConfig:
    def test_env_examples(self):
        be = (ROOT / "backend/.env.example").read_text(); fe = (ROOT / "frontend/.env.example").read_text()
        for k in ["MONGO_URL", "DB_NAME", "JWT_SECRET", "FRONTEND_URL", "CORS_ORIGINS", "CORS_ORIGIN_REGEX"]:
            assert re.search(rf"^{k}=", be, re.M), k
        assert re.search(r"^REACT_APP_BACKEND_URL=", fe, re.M)

    def test_vercel_and_middleware(self):
        v = (ROOT / "vercel.json").read_text(); json.loads(v)
        assert "emergent" not in v and "onrender" not in v
        m = (ROOT / "middleware.js").read_text()
        assert "process.env.BACKEND_URL" in m and "/api/:path*" in m

    def test_render_yaml(self):
        y = yaml.safe_load((ROOT / "render.yaml").read_text())
        names = [s["name"] for s in y["services"]]
        assert "perpus-backend" in names and "perpus-frontend" in names
        be = next(s for s in y["services"] if s["name"] == "perpus-backend")
        assert (ROOT / "backend" / be["buildCommand"].split()[-1]).exists()

    def test_no_emergent_in_runtime_code(self):
        hits = []
        for d, exts in [("frontend/src", (".js", ".jsx", ".ts", ".tsx", ".css")), ("backend", (".py",))]:
            for p in (ROOT / d).rglob("*"):
                if p.suffix in exts and "node_modules" not in p.parts and "tests" not in p.parts and not p.name.startswith("backend_test"):
                    t = p.read_text(errors="ignore")
                    if re.search(r"emergentagent\.com|emergent\.host|assets\.emergent\.sh", t): hits.append(str(p))
        assert not hits, hits
