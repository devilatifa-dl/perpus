# Iteration 20: Hapus laporan & Pulihkan data WITHOUT email code
import io, os, subprocess, time, zipfile
import pytest, requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
PY = "/root/.venv/bin/python"
SEED = "/app/backend/tests/seed_old_reports.py"
db = MongoClient("mongodb://localhost:27017")["test_database"]


def seed():
    subprocess.run([PY, SEED], check=True, capture_output=True)


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


def post(path, body, h):
    return requests.post(f"{API}{path}", json=body, headers=h)


# --- Purge without code ---
def test_purge_petugas_403(petugas):
    seed()
    r = post("/reports/purge", {"type": "masuk", "mode": "tahun", "year": 2024}, petugas)
    assert r.status_code == 403
    assert db.incoming.count_documents({"id": {"$regex": "^IN-OLD"}}) == 6


@pytest.mark.parametrize("t,coll,rx", [("masuk", "incoming", "^IN-OLD"), ("hilang", "missing", "^LS-OLD"), ("kunjungan", "visits", "^VS-OLD")])
def test_purge_year_no_code_over5(admin, t, coll, rx):
    seed()
    r = post("/reports/purge", {"type": t, "mode": "tahun", "year": 2024}, admin)
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] >= 6
    assert db[coll].count_documents({"id": {"$regex": rx}}) == 0


def test_purge_transaksi_year_protects_active(admin):
    seed()
    loans = requests.get(f"{API}/reports", headers=admin).json()["loans"]
    active = {l["id"] for l in loans if l["status"] == "Dipinjam"}
    r = post("/reports/purge", {"type": "transaksi", "mode": "tahun", "year": 2024}, admin)
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] >= 6
    assert db.transactions.count_documents({"id": {"$regex": "^TRX-OLD"}}) == 0
    loans2 = requests.get(f"{API}/reports", headers=admin).json()["loans"]
    assert {l["id"] for l in loans2 if l["status"] == "Dipinjam"} == active


def test_purge_active_loan_only_400(admin):
    loans = requests.get(f"{API}/reports", headers=admin).json()["loans"]
    act = [l for l in loans if l["status"] == "Dipinjam"]
    if not act:
        pytest.skip("no active loan")
    r = post("/reports/purge", {"type": "transaksi", "mode": "pilih", "ids": [act[0]["id"]]}, admin)
    assert r.status_code == 400
    assert db.transactions.count_documents({"id": act[0]["id"]}) == 1


def test_purge_pilih_and_rentang(admin):
    seed()
    r = post("/reports/purge", {"type": "hilang", "mode": "pilih", "ids": ["LS-OLD0", "LS-OLD1"]}, admin)
    assert r.status_code == 200 and r.json()["deleted"] == 2
    r = post("/reports/purge", {"type": "masuk", "mode": "rentang", "start": "2024-03-01", "end": "2024-05-31"}, admin)
    assert r.status_code == 200 and r.json()["deleted"] == 3
    assert {x["id"] for x in db.incoming.find({"id": {"$regex": "^IN-OLD"}})} == {"IN-OLD3", "IN-OLD4", "IN-OLD5"}
    seed()


def test_purge_backup_does_not_delete(admin):
    seed()
    r = post("/reports/purge/backup.xlsx", {"type": "masuk", "mode": "tahun", "year": 2024}, admin)
    assert r.status_code == 200 and "spreadsheetml" in r.headers["content-type"]
    assert db.incoming.count_documents({"id": {"$regex": "^IN-OLD"}}) == 6


# --- Restore without code ---
@pytest.fixture(scope="module")
def backup_bytes(admin):
    r = requests.get(f"{API}/admin/backup.zip", headers=admin, timeout=120)
    assert r.status_code == 200, r.text[:200]
    zipfile.ZipFile(io.BytesIO(r.content))  # valid zip
    with open("/tmp/backup_test.zip", "wb") as f:
        f.write(r.content)
    return r.content


def test_restore_petugas_403(petugas):
    r = post("/admin/restore/start", {"filename": "x.zip", "size": 10, "chunks": 1}, petugas)
    assert r.status_code == 403


def test_restore_chunked_no_code(admin, backup_bytes):
    books_before = db.books.count_documents({})
    users_before = db.users.count_documents({})
    r = post("/admin/restore/start", {"filename": "b.zip", "size": len(backup_bytes), "chunks": 1}, admin)
    assert r.status_code == 200, r.text
    uid = r.json()["upload_id"]
    r = requests.put(f"{API}/admin/restore/chunk", params={"upload_id": uid, "index": 0}, data=backup_bytes,
                     headers={**admin, "Content-Type": "application/octet-stream"})
    assert r.status_code == 200, r.text
    assert post("/admin/restore/finish", {"upload_id": uid}, admin).status_code == 200
    job = None
    for _ in range(60):
        job = requests.get(f"{API}/admin/restore/status/{uid}", headers=admin).json()
        if job["status"] in ("done", "error"):
            break
        time.sleep(1)
    assert job["status"] == "done", job
    assert db.books.count_documents({}) == books_before
    assert db.users.count_documents({}) == users_before


def test_restore_once_no_code(admin, backup_bytes):
    r = requests.post(f"{API}/admin/restore", headers=admin, files={"file": ("b.zip", backup_bytes, "application/zip")}, timeout=120)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_restore_invalid_file(admin):
    r = requests.post(f"{API}/admin/restore", headers=admin, files={"file": ("b.json", b"not json", "application/json")})
    assert r.status_code == 400
    assert db.books.count_documents({}) > 0
