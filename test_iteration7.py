"""Iteration 7 backend tests: text changes, stock feature, visitors, visit stats."""
import os, io, pytest, requests, time
from datetime import datetime, timedelta
from pathlib import Path

def _load_env():
    for p in [Path("/app/frontend/.env"), Path("/app/backend/.env")]:
        if p.exists():
            for line in p.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
_load_env()
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def login(portal, email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password, "portal": portal}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin():
    return login("admin", "admin@smansa.sch.id", "admin123")


@pytest.fixture(scope="module")
def petugas():
    return login("admin", "petugas@smansa.sch.id", "petugas123")


@pytest.fixture(scope="module")
def siswa():
    return login("siswa", "siswa@smansa.sch.id", "siswa123")


# ---------- Text changes ----------
class TestTextChanges:
    def test_admin_name_devi_latifa(self, admin):
        """Admin account should show 'Devi Latifa' not 'Administrator'"""
        r = admin.get(f"{BASE}/api/auth/me")
        assert r.status_code == 200
        user = r.json()
        assert user["name"] == "Devi Latifa, S.I.Pust", f"got '{user['name']}'"
        assert user["role"] == "admin"

    def test_settings_school_name(self, admin):
        """Settings should have 'SMA NEGERI 1 ABUNG TENGAH' not 'SMA 1 NEGERI ABUNG TENGAH'"""
        r = admin.get(f"{BASE}/api/settings")
        assert r.status_code == 200
        settings = r.json()
        assert settings["card_school_name"] == "SMA NEGERI 1 ABUNG TENGAH", \
            f"Expected 'SMA NEGERI 1 ABUNG TENGAH', got '{settings['card_school_name']}'"


# ---------- Stock feature ----------
class TestStockFeature:
    def test_book_has_stock_fields(self, admin):
        """Books should have stock, available, borrowed, lost fields"""
        r = admin.get(f"{BASE}/api/books")
        assert r.status_code == 200
        books = r.json()
        assert len(books) > 0
        for b in books:
            assert "stock" in b, f"Book {b['id']} missing 'stock' field"
            assert "available" in b, f"Book {b['id']} missing 'available' field"
            assert "borrowed" in b, f"Book {b['id']} missing 'borrowed' field"
            assert "lost" in b, f"Book {b['id']} missing 'lost' field"
            assert b["available"] == b["stock"] - b["borrowed"], \
                f"Book {b['id']}: available ({b['available']}) != stock ({b['stock']}) - borrowed ({b['borrowed']})"

    def test_add_book_with_stock(self, admin):
        """Adding a book should accept stock parameter"""
        r = admin.post(f"{BASE}/api/books", json={
            "title": "Test Stock Book",
            "author": "Test Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 5
        })
        assert r.status_code in (200, 201), r.text
        book = r.json()
        assert book["stock"] == 5
        assert book["available"] == 5
        assert book["borrowed"] == 0
        # cleanup
        admin.delete(f"{BASE}/api/books/{book['id']}")

    def test_add_same_book_merges_stock(self, admin):
        """Adding same title+author should merge stock"""
        # Add first book
        r1 = admin.post(f"{BASE}/api/books", json={
            "title": "Merge Test Book",
            "author": "Merge Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 3
        })
        assert r1.status_code in (200, 201)
        book1 = r1.json()
        book_id = book1["id"]
        
        # Add same book again
        r2 = admin.post(f"{BASE}/api/books", json={
            "title": "Merge Test Book",
            "author": "Merge Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 2
        })
        assert r2.status_code in (200, 201)
        book2 = r2.json()
        assert book2["merged"] == True, "Expected merged=True"
        assert book2["added"] == 2, "Expected added=2"
        assert book2["stock"] == 5, f"Expected stock=5, got {book2['stock']}"
        assert book2["id"] == book_id, "Should return same book ID"
        
        # Verify only one book exists
        books = admin.get(f"{BASE}/api/books").json()
        merge_books = [b for b in books if b["title"] == "Merge Test Book"]
        assert len(merge_books) == 1, f"Expected 1 book, found {len(merge_books)}"
        
        # cleanup
        admin.delete(f"{BASE}/api/books/{book_id}")

    def test_set_stock(self, admin):
        """Should be able to set stock via PATCH /books/{id}/stock"""
        # Create book
        r = admin.post(f"{BASE}/api/books", json={
            "title": "Stock Set Test",
            "author": "Test Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 5
        })
        book = r.json()
        book_id = book["id"]
        
        # Set stock to 10
        r2 = admin.patch(f"{BASE}/api/books/{book_id}/stock", json={"stock": 10})
        assert r2.status_code == 200
        updated = r2.json()
        assert updated["stock"] == 10
        assert updated["available"] == 10
        
        # cleanup
        admin.delete(f"{BASE}/api/books/{book_id}")

    def test_cannot_set_stock_below_borrowed(self, admin):
        """Cannot set stock below borrowed count"""
        # Create book and borrow it
        r = admin.post(f"{BASE}/api/books", json={
            "title": "Borrowed Stock Test",
            "author": "Test Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 5
        })
        book = r.json()
        book_id = book["id"]
        
        # Borrow 2 copies
        admin.post(f"{BASE}/api/transactions", json={
            "member_id": "MB-2024001",
            "book_id": book_id,
            "action": "pinjam"
        })
        
        # Try to set stock to 0 (should fail)
        r2 = admin.patch(f"{BASE}/api/books/{book_id}/stock", json={"stock": 0})
        assert r2.status_code == 400
        assert "tidak boleh kurang dari" in r2.json()["detail"].lower()
        
        # Return book and cleanup
        admin.post(f"{BASE}/api/transactions", json={
            "member_id": "MB-2024001",
            "book_id": book_id,
            "action": "kembali"
        })
        admin.delete(f"{BASE}/api/books/{book_id}")

    def test_circulation_reduces_available(self, admin):
        """Borrowing should reduce available, returning should increase"""
        # Create book
        r = admin.post(f"{BASE}/api/books", json={
            "title": "Circulation Test",
            "author": "Test Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 5
        })
        book = r.json()
        book_id = book["id"]
        
        # Borrow
        r2 = admin.post(f"{BASE}/api/transactions", json={
            "member_id": "MB-2024001",
            "book_id": book_id,
            "action": "pinjam"
        })
        assert r2.status_code in (200, 201)
        
        # Check available decreased
        books = admin.get(f"{BASE}/api/books").json()
        book_after_borrow = [b for b in books if b["id"] == book_id][0]
        assert book_after_borrow["available"] == 4
        assert book_after_borrow["borrowed"] == 1
        assert book_after_borrow["stock"] == 5
        
        # Return
        r3 = admin.post(f"{BASE}/api/transactions", json={
            "member_id": "MB-2024001",
            "book_id": book_id,
            "action": "kembali"
        })
        assert r3.status_code in (200, 201)
        
        # Check available increased
        books = admin.get(f"{BASE}/api/books").json()
        book_after_return = [b for b in books if b["id"] == book_id][0]
        assert book_after_return["available"] == 5
        assert book_after_return["borrowed"] == 0
        
        # cleanup
        admin.delete(f"{BASE}/api/books/{book_id}")

    def test_lost_and_found_per_copy(self, admin):
        """Lost should reduce stock and increase lost count, found should restore"""
        # Create book
        r = admin.post(f"{BASE}/api/books", json={
            "title": "Lost Test Book",
            "author": "Test Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 5
        })
        book = r.json()
        book_id = book["id"]
        
        # Mark as lost
        r2 = admin.patch(f"{BASE}/api/books/{book_id}/status", json={
            "status": "Hilang",
            "note": "Test lost",
            "reporter": "Test"
        })
        assert r2.status_code == 200
        
        # Check stock decreased and lost increased
        books = admin.get(f"{BASE}/api/books").json()
        book_after_lost = [b for b in books if b["id"] == book_id][0]
        assert book_after_lost["stock"] == 4, f"Expected stock=4, got {book_after_lost['stock']}"
        assert book_after_lost["lost"] == 1, f"Expected lost=1, got {book_after_lost['lost']}"
        
        # Mark as found
        r3 = admin.patch(f"{BASE}/api/books/{book_id}/status", json={
            "status": "Tersedia"
        })
        assert r3.status_code == 200
        
        # Check stock increased and lost decreased
        books = admin.get(f"{BASE}/api/books").json()
        book_after_found = [b for b in books if b["id"] == book_id][0]
        assert book_after_found["stock"] == 5
        assert book_after_found["lost"] == 0
        
        # cleanup
        admin.delete(f"{BASE}/api/books/{book_id}")

    def test_incoming_with_existing_title_adds_stock(self, admin):
        """Incoming with existing title should add to stock"""
        # Create book
        r = admin.post(f"{BASE}/api/books", json={
            "title": "Incoming Test Book",
            "author": "Incoming Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 3
        })
        book = r.json()
        book_id = book["id"]
        
        # Add incoming with same title
        r2 = admin.post(f"{BASE}/api/incoming", json={
            "title": "Incoming Test Book",
            "author": "Incoming Author",
            "category": "Umum",
            "shelf": "R-01",
            "quantity": 2,
            "source": "Test source"
        })
        assert r2.status_code in (200, 201)
        incoming = r2.json()
        assert incoming["merged"] == True
        assert incoming["stock_after"] == 5
        
        # Verify stock increased
        books = admin.get(f"{BASE}/api/books").json()
        book_after = [b for b in books if b["id"] == book_id][0]
        assert book_after["stock"] == 5
        
        # cleanup
        admin.delete(f"{BASE}/api/books/{book_id}")

    def test_dashboard_shows_lost_copies(self, admin):
        """Dashboard should show lost copies count"""
        r = admin.get(f"{BASE}/api/dashboard")
        assert r.status_code == 200
        stats = r.json()
        assert "missing" in stats
        assert isinstance(stats["missing"], int)


# ---------- Visitors feature ----------
class TestVisitors:
    def test_visitors_page_accessible(self, admin):
        """GET /api/visits should return today's visits"""
        r = admin.get(f"{BASE}/api/visits")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "summary" in data
        assert "checkout_time" in data
        assert isinstance(data["items"], list)
        assert "total" in data["summary"]
        assert "inside" in data["summary"]
        assert "anggota" in data["summary"]
        assert "tamu" in data["summary"]

    def test_scan_member_check_in(self, admin):
        """Scanning member code should check in"""
        r = admin.post(f"{BASE}/api/visits/scan", json={"code": "MB-2024002"})
        assert r.status_code in (200, 201)
        result = r.json()
        assert result["action"] in ["masuk", "sudah_masuk", "keluar"]
        assert "visit" in result
        assert "member" in result
        if result["action"] == "masuk":
            assert result["member"]["name"] == "Siti Rahma"

    def test_scan_nis_works(self, admin):
        """Scanning NIS should work like member code"""
        r = admin.post(f"{BASE}/api/visits/scan", json={"code": "24003"})
        assert r.status_code in (200, 201)
        result = r.json()
        assert result["action"] in ["masuk", "sudah_masuk", "keluar"]
        if result["action"] == "masuk":
            assert result["member"]["name"] == "Raka Wijaya"

    def test_scan_unknown_code_error(self, admin):
        """Scanning unknown code should return 404"""
        r = admin.post(f"{BASE}/api/visits/scan", json={"code": "UNKNOWN-CODE"})
        assert r.status_code == 404
        assert "tidak dikenal" in r.json()["detail"].lower()

    def test_guest_check_in(self, admin):
        """Adding guest should create visit record"""
        r = admin.post(f"{BASE}/api/visits/guest", json={
            "name": "Test Guest",
            "origin": "Test School",
            "purpose": "Membaca"
        })
        assert r.status_code in (200, 201)
        visit = r.json()
        assert visit["kind"] == "tamu"
        assert visit["name"] == "Test Guest"
        assert visit["origin"] == "Test School"
        assert visit["check_out"] is None
        # cleanup
        admin.delete(f"{BASE}/api/visits/{visit['id']}")

    def test_manual_checkout(self, admin):
        """Manual checkout should set check_out"""
        # Create guest visit
        r = admin.post(f"{BASE}/api/visits/guest", json={
            "name": "Checkout Test",
            "origin": "Test",
            "purpose": "Test"
        })
        visit = r.json()
        visit_id = visit["id"]
        
        # Manual checkout
        r2 = admin.post(f"{BASE}/api/visits/{visit_id}/checkout")
        assert r2.status_code == 200
        updated = r2.json()
        assert updated["check_out"] is not None
        assert updated["checkout_type"] == "manual"
        assert updated["duration_min"] is not None
        
        # cleanup
        admin.delete(f"{BASE}/api/visits/{visit_id}")

    def test_delete_visit(self, admin):
        """Should be able to delete visit record"""
        # Create guest visit
        r = admin.post(f"{BASE}/api/visits/guest", json={
            "name": "Delete Test",
            "origin": "Test",
            "purpose": "Test"
        })
        visit = r.json()
        visit_id = visit["id"]
        
        # Delete
        r2 = admin.delete(f"{BASE}/api/visits/{visit_id}")
        assert r2.status_code == 200

    def test_visit_config(self, admin):
        """Should be able to get and set checkout time"""
        # Get config
        r = admin.get(f"{BASE}/api/visits/config")
        assert r.status_code == 200
        config = r.json()
        assert "checkout_time" in config
        original_time = config["checkout_time"]
        
        # Set config
        r2 = admin.put(f"{BASE}/api/visits/config", json={"checkout_time": "15:00"})
        assert r2.status_code == 200
        assert r2.json()["checkout_time"] == "15:00"
        
        # Restore original
        admin.put(f"{BASE}/api/visits/config", json={"checkout_time": original_time})

    def test_dashboard_shows_visitors(self, admin):
        """Dashboard should show visitor counts"""
        r = admin.get(f"{BASE}/api/dashboard")
        assert r.status_code == 200
        stats = r.json()
        assert "visitors_today" in stats
        assert "visitors_inside" in stats
        assert isinstance(stats["visitors_today"], int)
        assert isinstance(stats["visitors_inside"], int)

    def test_siswa_cannot_access_visitors(self, siswa):
        """Siswa should not access visitor endpoints"""
        assert siswa.get(f"{BASE}/api/visits").status_code == 403
        assert siswa.post(f"{BASE}/api/visits/scan", json={"code": "MB-2024001"}).status_code == 403
        assert siswa.post(f"{BASE}/api/visits/guest", json={"name": "Test"}).status_code == 403


# ---------- Visit statistics ----------
class TestVisitStats:
    def test_visit_stats_endpoint(self, admin):
        """GET /api/visits/stats should return statistics"""
        r = admin.get(f"{BASE}/api/visits/stats", params={"period": "7hari"})
        assert r.status_code == 200
        stats = r.json()
        assert "period" in stats
        assert "total" in stats
        assert "avg_per_day" in stats
        assert "unique_members" in stats
        assert "kinds" in stats
        assert "per_day" in stats
        assert "per_class" in stats
        assert "per_hour" in stats
        assert isinstance(stats["kinds"], list)
        assert isinstance(stats["per_day"], list)
        assert isinstance(stats["per_class"], list)

    def test_visit_stats_periods(self, admin):
        """Should support different periods"""
        for period in ["harian", "7hari", "30hari", "bulanan", "semua"]:
            r = admin.get(f"{BASE}/api/visits/stats", params={"period": period})
            assert r.status_code == 200, f"Period {period} failed"
            stats = r.json()
            assert stats["period"] == period

    def test_visit_stats_has_percentages(self, admin):
        """Stats should include percentages"""
        r = admin.get(f"{BASE}/api/visits/stats", params={"period": "semua"})
        assert r.status_code == 200
        stats = r.json()
        for kind in stats["kinds"]:
            assert "pct" in kind
            assert isinstance(kind["pct"], (int, float))
        for cls in stats["per_class"]:
            assert "pct" in cls
            assert isinstance(cls["pct"], (int, float))

    def test_visit_history(self, admin):
        """GET /api/visits/history should return visit list"""
        r = admin.get(f"{BASE}/api/visits/history", params={"period": "semua"})
        assert r.status_code == 200
        visits = r.json()
        assert isinstance(visits, list)


# ---------- Reports with visits ----------
class TestReportsWithVisits:
    def test_export_kunjungan_pdf(self, admin):
        """Should export visit report as PDF"""
        r = admin.get(f"{BASE}/api/reports/export.pdf", params={"type": "kunjungan", "period": "semua"})
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert "laporan-kunjungan" in r.headers.get("content-disposition", "")

    def test_export_kunjungan_xlsx(self, admin):
        """Should export visit report as Excel"""
        r = admin.get(f"{BASE}/api/reports/export.xlsx", params={"type": "kunjungan", "period": "semua"})
        assert r.status_code == 200
        assert "spreadsheet" in r.headers["content-type"]
        assert "laporan-kunjungan" in r.headers.get("content-disposition", "")

    def test_export_statistik_pdf(self, admin):
        """Should export statistics report as PDF"""
        r = admin.get(f"{BASE}/api/reports/export.pdf", params={"type": "statistik", "period": "7hari"})
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert "laporan-statistik" in r.headers.get("content-disposition", "")

    def test_export_statistik_xlsx(self, admin):
        """Should export statistics report as Excel"""
        r = admin.get(f"{BASE}/api/reports/export.xlsx", params={"type": "statistik", "period": "7hari"})
        assert r.status_code == 200
        assert "spreadsheet" in r.headers["content-type"]
        assert "laporan-statistik" in r.headers.get("content-disposition", "")


# ---------- Regression tests ----------
class TestRegression:
    def test_existing_reports_still_work(self, admin):
        """Existing report types should still work"""
        for report_type in ["transaksi", "masuk", "hilang"]:
            r = admin.get(f"{BASE}/api/reports/export.pdf", params={"type": report_type, "period": "semua"})
            assert r.status_code == 200, f"Report type {report_type} failed"

    def test_stocktake_still_works(self, admin):
        """Stocktake should still work"""
        r = admin.post(f"{BASE}/api/stocktake", json={
            "shelf": "R-01",
            "scanned": ["BK-1042"],
            "unscanned": [],
            "misplaced": []
        })
        assert r.status_code == 200

    def test_reservation_approve_decrements_stock(self, admin, siswa):
        """Approving reservation should decrement available stock"""
        # Create book
        r = admin.post(f"{BASE}/api/books", json={
            "title": "Reservation Stock Test",
            "author": "Test Author",
            "category": "Umum",
            "shelf": "R-01",
            "stock": 5
        })
        book = r.json()
        book_id = book["id"]
        
        # Create reservation
        r2 = siswa.post(f"{BASE}/api/reservations", json={"book_id": book_id})
        assert r2.status_code in (200, 201)
        res = r2.json()
        res_id = res["id"]
        
        # Approve reservation
        r3 = admin.post(f"{BASE}/api/reservations/{res_id}/process", json={"action": "pinjam"})
        assert r3.status_code == 200
        
        # Check stock decreased
        books = admin.get(f"{BASE}/api/books").json()
        book_after = [b for b in books if b["id"] == book_id][0]
        assert book_after["available"] == 4
        assert book_after["borrowed"] == 1
        
        # Return and cleanup
        admin.post(f"{BASE}/api/transactions", json={
            "member_id": "MB-2024001",
            "book_id": book_id,
            "action": "kembali"
        })
        admin.delete(f"{BASE}/api/books/{book_id}")
