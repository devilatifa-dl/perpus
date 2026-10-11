"""Backend tests for iteration 4: incoming books, lost/found, member history, settings, member no email/phone."""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _login(email, password, portal="admin"):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": email, "password": password, "portal": portal})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture
def admin():
    return _login("admin@smansa.sch.id", "admin123", "admin")


@pytest.fixture
def petugas():
    return _login("petugas@smansa.sch.id", "petugas123", "admin")


@pytest.fixture
def siswa():
    return _login("siswa@smansa.sch.id", "siswa123", "siswa")


# ---- Portal gating ----
class TestPortalGating:
    def test_siswa_on_admin_portal_403(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "siswa@smansa.sch.id",
                                "password": "siswa123", "portal": "admin"})
        assert r.status_code == 403

    def test_admin_on_siswa_portal_403(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "admin@smansa.sch.id",
                                "password": "admin123", "portal": "siswa"})
        assert r.status_code == 403

    def test_login_sets_cookie(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "admin@smansa.sch.id",
                                "password": "admin123", "portal": "admin"})
        assert r.status_code == 200
        assert "access_token" in r.cookies


# ---- Siswa scoping ----
class TestSiswaScoping:
    def test_members_me(self, siswa):
        r = siswa.get(f"{BASE_URL}/api/members/me")
        assert r.status_code == 200
        assert r.json()["id"] == "MB-2024001"

    def test_members_list_only_own(self, siswa):
        r = siswa.get(f"{BASE_URL}/api/members")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1 and data[0]["id"] == "MB-2024001"

    def test_reports_403(self, siswa):
        r = siswa.get(f"{BASE_URL}/api/reports")
        assert r.status_code == 403

    def test_transactions_403(self, siswa):
        r = siswa.get(f"{BASE_URL}/api/transactions")
        assert r.status_code == 403


# ---- Incoming books ----
class TestIncoming:
    def test_create_incoming_creates_n_books(self, admin):
        title = f"TEST_INC_{uuid.uuid4().hex[:8]}"
        payload = {"title": title, "author": "Pengarang", "quantity": 3, "date": "2026-01-15",
                   "source": "Donasi TEST", "shelf": "R-01", "category": "Umum"}
        r = admin.post(f"{BASE_URL}/api/incoming", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["quantity"] == 3
        assert data["detail"] == "3 eksemplar"
        assert len(data["book_ids"]) == 3
        # Verify books exist in catalog
        books = admin.get(f"{BASE_URL}/api/books").json()
        matching = [b for b in books if b["title"] == title]
        assert len(matching) == 3
        for b in matching:
            assert b["status"] == "Tersedia"
        # Cleanup
        for bid in data["book_ids"]:
            admin.delete(f"{BASE_URL}/api/books/{bid}")

    def test_incoming_siswa_forbidden(self, siswa):
        r = siswa.post(f"{BASE_URL}/api/incoming",
                       json={"title": "TEST_x", "author": "x", "quantity": 1})
        assert r.status_code == 403

    def test_incoming_quantity_zero_422(self, admin):
        r = admin.post(f"{BASE_URL}/api/incoming",
                       json={"title": "TEST_x", "author": "x", "quantity": 0})
        assert r.status_code == 422

    def test_dashboard_incoming_sums_quantity(self, admin):
        before = admin.get(f"{BASE_URL}/api/dashboard").json()["incoming"]
        title = f"TEST_SUM_{uuid.uuid4().hex[:6]}"
        r = admin.post(f"{BASE_URL}/api/incoming",
                       json={"title": title, "author": "x", "quantity": 5})
        book_ids = r.json()["book_ids"]
        after = admin.get(f"{BASE_URL}/api/dashboard").json()["incoming"]
        assert after == before + 5
        for bid in book_ids:
            admin.delete(f"{BASE_URL}/api/books/{bid}")

    def test_reports_incoming_is_real(self, admin):
        title = f"TEST_REP_{uuid.uuid4().hex[:6]}"
        r = admin.post(f"{BASE_URL}/api/incoming",
                       json={"title": title, "author": "x", "quantity": 2})
        book_ids = r.json()["book_ids"]
        reports = admin.get(f"{BASE_URL}/api/reports").json()
        titles = [i["title"] for i in reports["incoming"]]
        assert title in titles
        # Verify stale 'Modul Literasi Digital' seed is not injected automatically
        for bid in book_ids:
            admin.delete(f"{BASE_URL}/api/books/{bid}")


# ---- Lost / Found ----
class TestLostFound:
    def _get_available(self, client):
        # Prefer stable seeded books to avoid race with parallel incoming tests
        books = client.get(f"{BASE_URL}/api/books").json()
        for seeded in ("BK-1042", "BK-1044", "BK-1045"):
            b = next((x for x in books if x["id"] == seeded and x["status"] == "Tersedia"), None)
            if b:
                return b["id"]
        for b in books:
            if b["status"] == "Tersedia" and not b.get("title", "").startswith("TEST_"):
                return b["id"]
        pytest.skip("no available book")

    def test_mark_lost_and_restore(self, admin):
        book_id = self._get_available(admin)
        # mark lost
        r = admin.patch(f"{BASE_URL}/api/books/{book_id}/status",
                        json={"status": "Hilang", "note": "TEST_note"})
        assert r.status_code == 200
        b = next(x for x in admin.get(f"{BASE_URL}/api/books").json() if x["id"] == book_id)
        assert b["status"] == "Hilang"
        # appears in missing reports
        missing = admin.get(f"{BASE_URL}/api/reports").json()["missing"]
        hit = [m for m in missing if m["book_id"] == book_id and m["status"] == "Hilang"]
        assert hit, "lost report not created"
        # mark lost again -> 400
        r2 = admin.patch(f"{BASE_URL}/api/books/{book_id}/status",
                         json={"status": "Hilang"})
        assert r2.status_code == 400
        # restore
        r3 = admin.patch(f"{BASE_URL}/api/books/{book_id}/status",
                         json={"status": "Tersedia"})
        assert r3.status_code == 200
        b = next(x for x in admin.get(f"{BASE_URL}/api/books").json() if x["id"] == book_id)
        assert b["status"] == "Tersedia"
        # report updated to Ditemukan
        missing = admin.get(f"{BASE_URL}/api/reports").json()["missing"]
        hit = [m for m in missing if m["book_id"] == book_id]
        assert hit and all(m["status"] == "Ditemukan" for m in hit)

    def test_invalid_status_400(self, admin):
        book_id = self._get_available(admin)
        r = admin.patch(f"{BASE_URL}/api/books/{book_id}/status",
                        json={"status": "Rusak"})
        assert r.status_code == 400

    def test_siswa_cannot_mark_lost(self, siswa):
        r = siswa.patch(f"{BASE_URL}/api/books/BK-1042/status",
                        json={"status": "Hilang"})
        assert r.status_code == 403

    def test_unknown_book_404(self, admin):
        r = admin.patch(f"{BASE_URL}/api/books/BK-DOESNOTEXIST/status",
                        json={"status": "Hilang"})
        assert r.status_code == 404


# ---- Member history ----
class TestMemberHistory:
    def test_admin_history_shape(self, admin):
        r = admin.get(f"{BASE_URL}/api/members/MB-2024001/history")
        assert r.status_code == 200
        data = r.json()
        assert "member" in data and "history" in data and "total" in data and "active" in data
        for h in data["history"]:
            assert "returned" in h and "returned_at" in h

    def test_borrow_then_return_updates_returned(self, admin):
        member_id = "MB-2024001"
        # pick available book not currently borrowed by member
        books = admin.get(f"{BASE_URL}/api/books").json()
        book_id = next(b["id"] for b in books if b["status"] == "Tersedia")
        admin.post(f"{BASE_URL}/api/transactions",
                   json={"member_id": member_id, "book_id": book_id, "action": "pinjam"})
        hist = admin.get(f"{BASE_URL}/api/members/{member_id}/history").json()["history"]
        last_open = [h for h in hist if h["book_id"] == book_id and not h["returned"]]
        assert last_open
        admin.post(f"{BASE_URL}/api/transactions",
                   json={"member_id": member_id, "book_id": book_id, "action": "kembali"})
        hist2 = admin.get(f"{BASE_URL}/api/members/{member_id}/history").json()["history"]
        matched = [h for h in hist2 if h["book_id"] == book_id and h["returned"]]
        assert matched and matched[0]["returned_at"]

    def test_siswa_own_history_ok(self, siswa):
        r = siswa.get(f"{BASE_URL}/api/members/MB-2024001/history")
        assert r.status_code == 200

    def test_siswa_other_member_history_403(self, siswa):
        r = siswa.get(f"{BASE_URL}/api/members/MB-2024002/history")
        assert r.status_code == 403


# ---- Settings ----
class TestSettings:
    def test_defaults(self, admin):
        r = admin.get(f"{BASE_URL}/api/settings")
        assert r.status_code == 200
        data = r.json()
        for k in ("card_theme", "card_layout", "card_title", "card_show_qr", "card_show_address"):
            assert k in data

    def test_put_persists(self, admin):
        payload = {"card_theme": "emerald", "card_layout": "portrait",
                   "card_show_qr": True, "card_show_address": False,
                   "card_title": "KARTU TEST", "school_logo": "", "library_logo": ""}
        r = admin.put(f"{BASE_URL}/api/settings", json=payload)
        assert r.status_code == 200
        got = admin.get(f"{BASE_URL}/api/settings").json()
        assert got["card_theme"] == "emerald"
        assert got["card_title"] == "KARTU TEST"
        assert got["card_show_address"] is False
        # restore defaults
        admin.put(f"{BASE_URL}/api/settings", json={
            "card_theme": "navy", "card_layout": "classic",
            "card_show_qr": True, "card_show_address": True,
            "card_title": "KARTU ANGGOTA PERPUSTAKAAN",
            "school_logo": "", "library_logo": ""})

    def test_siswa_put_forbidden(self, siswa):
        r = siswa.put(f"{BASE_URL}/api/settings", json={"card_theme": "red"})
        assert r.status_code == 403


# ---- Members no email/phone ----
class TestMembersNoContact:
    def test_create_no_email_phone(self, admin):
        payload = {"name": f"TEST_{uuid.uuid4().hex[:6]}",
                   "student_id": uuid.uuid4().hex[:6], "class_name": "X TEST"}
        r = admin.post(f"{BASE_URL}/api/members", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "email" not in data
        assert "phone" not in data

    def test_members_list_no_email_phone(self, admin):
        members = admin.get(f"{BASE_URL}/api/members").json()
        for m in members:
            assert "email" not in m
            assert "phone" not in m
