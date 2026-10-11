import os
import uuid
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _login(email, password, portal="admin"):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password, "portal": portal})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture
def staff():
    return _login("petugas@smansa.sch.id", "petugas123", "admin")


@pytest.fixture
def admin():
    return _login("admin@smansa.sch.id", "admin123", "admin")


@pytest.fixture
def siswa():
    return _login("siswa@smansa.sch.id", "siswa123", "siswa")


# --- Reports loans array ---
def test_reports_contains_loans_array(staff):
    r = staff.get(f"{BASE_URL}/api/reports")
    assert r.status_code == 200
    data = r.json()
    assert "loans" in data and isinstance(data["loans"], list)
    for loan in data["loans"]:
        assert loan["status"] in ("Dipinjam", "Dikembalikan")
        for k in ("member_name", "book_title", "book_id", "borrowed_at", "returned_at"):
            assert k in loan


def test_loan_pinjam_then_kembali_state(staff):
    # Find an available book
    books = staff.get(f"{BASE_URL}/api/books").json()
    avail = next((b for b in books if b["status"] == "Tersedia"), None)
    assert avail
    members = staff.get(f"{BASE_URL}/api/members").json()
    mid = members[0]["id"]
    # pinjam
    pr = staff.post(f"{BASE_URL}/api/transactions", json={"member_id": mid, "book_id": avail["id"], "action": "pinjam"})
    assert pr.status_code == 200
    loans = staff.get(f"{BASE_URL}/api/reports").json()["loans"]
    open_loan = next((l for l in loans if l["book_id"] == avail["id"] and l["status"] == "Dipinjam"), None)
    assert open_loan is not None
    assert open_loan["returned_at"] is None
    assert open_loan["borrowed_at"]
    # kembali
    kr = staff.post(f"{BASE_URL}/api/transactions", json={"member_id": mid, "book_id": avail["id"], "action": "kembali"})
    assert kr.status_code == 200
    loans = staff.get(f"{BASE_URL}/api/reports").json()["loans"]
    done = next((l for l in loans if l["book_id"] == avail["id"] and l["status"] == "Dikembalikan" and l["returned_at"]), None)
    assert done is not None


# --- Export PDF ---
@pytest.mark.parametrize("kind", ["transaksi", "masuk", "hilang"])
@pytest.mark.parametrize("period", ["semua", "harian", "bulanan"])
def test_export_pdf_ok(staff, kind, period):
    r = staff.get(f"{BASE_URL}/api/reports/export.pdf", params={"type": kind, "period": period})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd and ".pdf" in cd


def test_export_pdf_invalid_type(staff):
    r = staff.get(f"{BASE_URL}/api/reports/export.pdf", params={"type": "bogus"})
    assert r.status_code == 400


def test_export_pdf_siswa_forbidden(siswa):
    r = siswa.get(f"{BASE_URL}/api/reports/export.pdf", params={"type": "transaksi"})
    assert r.status_code == 403


def test_export_pdf_unauth():
    r = requests.get(f"{BASE_URL}/api/reports/export.pdf", params={"type": "transaksi"})
    assert r.status_code == 401


# --- Book status with reporter ---
def test_book_status_with_reporter_and_restore(staff):
    # Create a dedicated book
    cr = staff.post(f"{BASE_URL}/api/books", json={"title": f"TEST_LOST_{uuid.uuid4().hex[:6]}", "author": "T", "shelf": "R-01"})
    assert cr.status_code == 200
    bid = cr.json()["id"]
    try:
        # Mark Hilang with reporter
        r = staff.patch(f"{BASE_URL}/api/books/{bid}/status", json={"status": "Hilang", "note": "tidak ditemukan", "reporter": "Pak Budi"})
        assert r.status_code == 200
        reports = staff.get(f"{BASE_URL}/api/reports").json()["missing"]
        rep = next((m for m in reports if m["book_id"] == bid), None)
        assert rep is not None
        assert rep["reported_by"] == "Pak Budi"
        assert rep["detail"] == "tidak ditemukan"
        assert rep["status"] == "Hilang"
        # Restore
        r2 = staff.patch(f"{BASE_URL}/api/books/{bid}/status", json={"status": "Tersedia"})
        assert r2.status_code == 200
        reports = staff.get(f"{BASE_URL}/api/reports").json()["missing"]
        rep = next((m for m in reports if m["book_id"] == bid), None)
        assert rep is not None
        assert rep["status"] == "Ditemukan"
        assert rep.get("found_at")
    finally:
        staff.delete(f"{BASE_URL}/api/books/{bid}")


def test_book_status_without_reporter_falls_back_to_user(staff):
    cr = staff.post(f"{BASE_URL}/api/books", json={"title": f"TEST_LOST_{uuid.uuid4().hex[:6]}", "author": "T", "shelf": "R-01"})
    bid = cr.json()["id"]
    try:
        r = staff.patch(f"{BASE_URL}/api/books/{bid}/status", json={"status": "Hilang", "note": "x"})
        assert r.status_code == 200
        reports = staff.get(f"{BASE_URL}/api/reports").json()["missing"]
        rep = next((m for m in reports if m["book_id"] == bid), None)
        # staff fixture = petugas -> "Rina Pustakawan"
        assert rep["reported_by"] == "Rina Pustakawan"
        # cleanup state
        staff.patch(f"{BASE_URL}/api/books/{bid}/status", json={"status": "Tersedia"})
    finally:
        staff.delete(f"{BASE_URL}/api/books/{bid}")
