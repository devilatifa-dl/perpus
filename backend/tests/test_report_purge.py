# Report purge (Hapus laporan) feature tests: preview / backup / purge / logs, admin-only, protections
import io, os, subprocess
import pytest, requests
from openpyxl import load_workbook
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
PY = "/root/.venv/bin/python"
SEED = "/app/backend/tests/seed_old_reports.py"
db = MongoClient("mongodb://localhost:27017")["test_database"]


def seed(*args):
    subprocess.run([PY, SEED, *args], check=True, capture_output=True)


def login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw, "portal": "admin"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def admin():
    return login("admin@smansa.sch.id", "admin123")


@pytest.fixture(scope="module")
def petugas():
    return login("petugas@smansa.sch.id", "petugas123")


@pytest.fixture(autouse=True)
def reseed():
    seed()
    yield


def post(path, body, h):
    return requests.post(f"{API}{path}", json=body, headers=h)


def active_loans(h):
    loans = requests.get(f"{API}/reports", headers=h).json()["loans"]
    return [l for l in loans if l["status"] == "Dipinjam"]


# --- Admin only ---
def test_petugas_forbidden(petugas):
    for path in ["/reports/purge/preview", "/reports/purge/backup.xlsx", "/reports/purge"]:
        r = post(path, {"type": "masuk", "mode": "tahun", "year": 2024, "code": "123456"}, petugas)
        assert r.status_code == 403, (path, r.status_code)
    assert requests.get(f"{API}/reports/purge/logs", headers=petugas).status_code == 403
    assert db.incoming.count_documents({"id": {"$regex": "^IN-OLD"}}) == 6


def test_unauthenticated():
    r = requests.post(f"{API}/reports/purge/preview", json={"type": "masuk", "mode": "tahun", "year": 2024})
    assert r.status_code in (401, 403)


# --- Preview ---
@pytest.mark.parametrize("t", ["transaksi", "kunjungan", "masuk", "hilang"])
def test_preview_year_2024(admin, t):
    r = post("/reports/purge/preview", {"type": t, "mode": "tahun", "year": 2024}, admin)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["count"] >= 6 and d["label"] == "Tahun 2024" and "protected" in d


def test_preview_validation(admin):
    assert post("/reports/purge/preview", {"type": "masuk", "mode": "rentang", "start": "2024-12-01", "end": "2024-01-01"}, admin).status_code == 400
    assert post("/reports/purge/preview", {"type": "masuk", "mode": "rentang", "start": "", "end": ""}, admin).status_code == 400
    assert post("/reports/purge/preview", {"type": "xxx", "mode": "tahun", "year": 2024}, admin).status_code == 400
    assert post("/reports/purge/preview", {"type": "masuk", "mode": "pilih", "ids": []}, admin).status_code == 400
    assert post("/reports/purge/preview", {"type": "masuk", "mode": "tahun", "year": 1990}, admin).status_code == 400
    assert post("/reports/purge/preview", {"type": "masuk", "mode": "bad"}, admin).status_code == 422


def test_preview_rentang(admin):
    # seeded dates 2024-03-10 .. 2024-08-10 -> Mar..May = 3
    r = post("/reports/purge/preview", {"type": "masuk", "mode": "rentang", "start": "2024-03-01", "end": "2024-05-31"}, admin)
    assert r.status_code == 200 and r.json()["count"] == 3, r.text


def test_active_loan_protected(admin):
    act = active_loans(admin)
    assert act, "expected at least one active loan (Bima Pratama)"
    l = act[0]
    year = int(l["borrowed_at"][:4])
    r = post("/reports/purge/preview", {"type": "transaksi", "mode": "pilih", "ids": [l["id"]]}, admin)
    assert r.status_code == 200 and r.json()["count"] == 0 and r.json()["protected"] == 1, r.text
    r = post("/reports/purge/preview", {"type": "transaksi", "mode": "tahun", "year": year}, admin)
    assert r.json()["protected"] >= 1
    # purge with pilih on only active -> 400 nothing to delete
    seed("code")
    r = post("/reports/purge", {"type": "transaksi", "mode": "pilih", "ids": [l["id"]], "code": "123456"}, admin)
    assert r.status_code == 400
    assert db.transactions.count_documents({"id": l["id"]}) == 1


def test_visit_without_checkout_protected(admin):
    db.visits.update_one({"id": "VS-OLD0"}, {"$set": {"check_out": None}})
    r = post("/reports/purge/preview", {"type": "kunjungan", "mode": "pilih", "ids": ["VS-OLD0", "VS-OLD1"]}, admin)
    d = r.json()
    # visits_auto_close may close old open visits; either it's protected or got auto-closed
    v = db.visits.find_one({"id": "VS-OLD0"}, {"_id": 0})
    print("VS-OLD0 after preview:", v.get("check_out"), d)
    if not v.get("check_out"):
        assert d["count"] == 1 and d["protected"] == 1
    else:
        assert d["count"] == 2


# --- Backup ---
@pytest.mark.parametrize("t", ["transaksi", "kunjungan", "masuk", "hilang"])
def test_backup_xlsx(admin, t):
    r = post("/reports/purge/backup.xlsx", {"type": t, "mode": "tahun", "year": 2024}, admin)
    assert r.status_code == 200, r.text[:300]
    assert "spreadsheetml" in r.headers["content-type"]
    assert "attachment" in r.headers.get("content-disposition", "")
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb.active
    text = " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)
    assert ws.max_row >= 7
    if t == "masuk":
        assert "Buku Lama 0" in text
    if t == "transaksi":
        assert "Laskar Pelangi" in text


# --- Purge with code ---
def test_purge_transaksi_year(admin):
    before_active = {l["id"] for l in active_loans(admin)}
    book_before = db.books.find_one({"id": "BK-1042"}, {"_id": 0, "stock": 1, "borrowed": 1})
    seed("code")
    r = post("/reports/purge", {"type": "transaksi", "mode": "tahun", "year": 2024, "code": "123456"}, admin)
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] >= 6
    assert db.transactions.count_documents({"id": {"$regex": "^TRX-OLD"}}) == 0  # both P and K gone
    assert {l["id"] for l in active_loans(admin)} == before_active
    book_after = db.books.find_one({"id": "BK-1042"}, {"_id": 0, "stock": 1, "borrowed": 1})
    assert book_before == book_after
    logs = requests.get(f"{API}/reports/purge/logs", headers=admin).json()
    assert logs[0]["type"] == "transaksi" and logs[0]["label"] == "Tahun 2024" and logs[0]["documents"] >= 12


def test_purge_pilih_only_ids(admin):
    seed("code")
    r = post("/reports/purge", {"type": "hilang", "mode": "pilih", "ids": ["LS-OLD0", "LS-OLD1"], "code": "123456"}, admin)
    assert r.status_code == 200 and r.json()["deleted"] == 2, r.text
    left = {x["id"] for x in db.missing.find({"id": {"$regex": "^LS-OLD"}})}
    assert left == {"LS-OLD2", "LS-OLD3", "LS-OLD4", "LS-OLD5"}


def test_purge_pilih_transaksi(admin):
    seed("code")
    r = post("/reports/purge", {"type": "transaksi", "mode": "pilih", "ids": ["TRX-OLD2P"], "code": "123456"}, admin)
    assert r.status_code == 200 and r.json()["deleted"] == 1, r.text
    left = {x["id"] for x in db.transactions.find({"id": {"$regex": "^TRX-OLD"}})}
    assert "TRX-OLD2P" not in left and "TRX-OLD2K" not in left and len(left) == 10


def test_purge_rentang_kunjungan(admin):
    seed("code")
    r = post("/reports/purge", {"type": "kunjungan", "mode": "rentang", "start": "2024-03-01", "end": "2024-04-30", "code": "123456"}, admin)
    assert r.status_code == 200 and r.json()["deleted"] == 2, r.text
    left = {x["id"] for x in db.visits.find({"id": {"$regex": "^VS-OLD"}})}
    assert left == {"VS-OLD2", "VS-OLD3", "VS-OLD4", "VS-OLD5"}


def test_purge_logs_shape(admin):
    r = requests.get(f"{API}/reports/purge/logs", headers=admin)
    assert r.status_code == 200 and isinstance(r.json(), list)
    if r.json():
        assert {"id", "type", "label", "rows", "documents", "by", "at"} <= set(r.json()[0])
        assert "_id" not in r.json()[0]
