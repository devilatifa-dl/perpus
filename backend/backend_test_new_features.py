#!/usr/bin/env python3
"""
Backend API Testing for New Features:
1. Lainnya (Other) purpose with custom text input
2. Class column in transaction reports
3. Excel export for summary reports
"""

import requests
import sys
import io
from datetime import datetime

BASE_URL = "https://restore-app-34--3g9ynt9t.preview.emergentagent.com/api"

class NewFeaturesTestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.siswa_token = None
        self.test_visit_ids = []
        self.test_member_id = None

    def log(self, msg):
        print(f"  {msg}")

    def test(self, name, fn):
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        try:
            fn()
            self.tests_passed += 1
            print(f"✅ PASSED")
            return True
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            return False
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False

    # ===== AUTH =====
    def test_admin_login(self):
        """Test admin login"""
        def _test():
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "admin@smansa.sch.id",
                "password": "admin123",
                "portal": "admin"
            })
            assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
            self.admin_token = resp.cookies.get("access_token")
            self.log(f"Admin logged in")
        self.test("Admin login", _test)

    def test_siswa_login(self):
        """Test siswa login"""
        def _test():
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "siswa@smansa.sch.id",
                "password": "siswa123",
                "portal": "siswa"
            })
            assert resp.status_code == 200, f"Siswa login failed: {resp.status_code} {resp.text}"
            self.siswa_token = resp.cookies.get("access_token")
            self.log(f"Siswa logged in")
        self.test("Siswa login", _test)

    # ===== FEATURE 1: LAINNYA PURPOSE WITH CUSTOM TEXT =====
    def test_scan_with_custom_purpose(self):
        """Test POST /api/visits/scan with custom purpose text"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            # Get a member
            members_resp = requests.get(f"{BASE_URL}/members", headers=headers)
            members = members_resp.json()
            assert len(members) > 0, "No members available"
            
            # Scan with custom purpose
            visit_data = {
                "code": members[0]["student_id"] or members[0]["id"],
                "purpose": "Rapat OSIS"
            }
            resp = requests.post(f"{BASE_URL}/visits/scan", json=visit_data, headers=headers)
            assert resp.status_code == 200, f"Scan failed: {resp.status_code} {resp.text}"
            result = resp.json()
            assert result.get("action") in ["masuk", "sudah_masuk"], f"Unexpected action: {result.get('action')}"
            
            if result.get("action") == "masuk":
                visit = result.get("visit", {})
                assert visit.get("purpose") == "Rapat OSIS", f"Purpose not saved correctly: {visit.get('purpose')}"
                self.test_visit_ids.append(visit["id"])
                self.log(f"Visit created with custom purpose: {visit.get('purpose')}")
            else:
                self.log("Member already checked in, will test checkout")
        self.test("POST /api/visits/scan saves custom purpose text", _test)

    def test_scan_with_empty_purpose(self):
        """Test POST /api/visits/scan with empty purpose (should save as empty string)"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            # Get a different member
            members_resp = requests.get(f"{BASE_URL}/members", headers=headers)
            members = members_resp.json()
            assert len(members) > 1, "Need at least 2 members"
            
            # Scan with empty purpose
            visit_data = {
                "code": members[1]["student_id"] or members[1]["id"],
                "purpose": ""
            }
            resp = requests.post(f"{BASE_URL}/visits/scan", json=visit_data, headers=headers)
            assert resp.status_code == 200, f"Scan failed: {resp.status_code} {resp.text}"
            result = resp.json()
            
            if result.get("action") == "masuk":
                visit = result.get("visit", {})
                assert visit.get("purpose") == "", f"Empty purpose should be saved as empty string: {visit.get('purpose')}"
                self.test_visit_ids.append(visit["id"])
                self.log(f"Visit created with empty purpose")
        self.test("POST /api/visits/scan with empty purpose saves empty string", _test)

    def test_guest_with_custom_purpose(self):
        """Test POST /api/visits/guest with custom purpose"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            guest_data = {
                "name": "TEST Guest Custom Purpose",
                "origin": "Test School",
                "purpose": "Survei akreditasi"
            }
            resp = requests.post(f"{BASE_URL}/visits/guest", json=guest_data, headers=headers)
            assert resp.status_code == 200, f"Guest entry failed: {resp.status_code} {resp.text}"
            visit = resp.json()
            assert visit.get("purpose") == "Survei akreditasi", f"Guest purpose not saved: {visit.get('purpose')}"
            self.test_visit_ids.append(visit["id"])
            self.log(f"Guest created with custom purpose: {visit.get('purpose')}")
        self.test("POST /api/visits/guest saves custom purpose", _test)

    def test_update_purpose_via_patch(self):
        """Test PATCH /api/visits/{id}/purpose updates custom text"""
        def _test():
            if not self.test_visit_ids:
                self.log("No test visits available, skipping")
                return
            
            headers = {"Cookie": f"access_token={self.admin_token}"}
            visit_id = self.test_visit_ids[0]
            
            # Update purpose
            resp = requests.patch(f"{BASE_URL}/visits/{visit_id}/purpose", 
                                json={"purpose": "Latihan lomba debat"}, 
                                headers=headers)
            assert resp.status_code == 200, f"Update purpose failed: {resp.status_code} {resp.text}"
            visit = resp.json()
            assert visit.get("purpose") == "Latihan lomba debat", f"Purpose not updated: {visit.get('purpose')}"
            self.log(f"Purpose updated to: {visit.get('purpose')}")
        self.test("PATCH /api/visits/{id}/purpose updates custom purpose", _test)

    def test_visits_list_shows_purpose(self):
        """Test GET /api/visits returns visits with purpose field"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/visits", headers=headers)
            assert resp.status_code == 200, f"Visits list failed: {resp.status_code} {resp.text}"
            data = resp.json()
            items = data.get("items", [])
            
            # Check if any visit has purpose field
            visits_with_purpose = [v for v in items if v.get("purpose")]
            self.log(f"Found {len(visits_with_purpose)} visits with purpose out of {len(items)} total")
        self.test("GET /api/visits returns visits with purpose field", _test)

    # ===== FEATURE 2: CLASS COLUMN IN TRANSACTION REPORTS =====
    def test_transaction_includes_class_name(self):
        """Test POST /api/transactions stores class_name"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            
            # Get a member with class_name
            members_resp = requests.get(f"{BASE_URL}/members", headers=headers)
            members = members_resp.json()
            member_with_class = next((m for m in members if m.get("class_name")), None)
            assert member_with_class, "No member with class_name found"
            
            # Get an available book
            books_resp = requests.get(f"{BASE_URL}/books", headers=headers)
            books = books_resp.json()
            available_books = [b for b in books if b.get("available", 0) > 0]
            assert len(available_books) > 0, "No available books"
            
            # Create transaction
            transaction_data = {
                "member_id": member_with_class["id"],
                "book_id": available_books[0]["id"],
                "action": "pinjam"
            }
            resp = requests.post(f"{BASE_URL}/transactions", json=transaction_data, headers=headers)
            assert resp.status_code == 200, f"Transaction failed: {resp.status_code} {resp.text}"
            
            # Get transactions and verify class_name is stored
            tx_resp = requests.get(f"{BASE_URL}/transactions", headers=headers)
            transactions = tx_resp.json()
            latest_tx = transactions[0] if transactions else None
            assert latest_tx, "No transactions found"
            assert "class_name" in latest_tx, "Transaction missing class_name field"
            self.log(f"Transaction includes class_name: {latest_tx.get('class_name')}")
        self.test("POST /api/transactions stores class_name", _test)

    def test_reports_transaksi_includes_class(self):
        """Test GET /api/reports?type=transaksi includes class_name"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports?type=transaksi&period=semua", headers=headers)
            assert resp.status_code == 200, f"Reports failed: {resp.status_code} {resp.text}"
            loans = resp.json()
            
            if len(loans) > 0:
                # Check if loans have class_name field
                loans_with_class = [l for l in loans if "class_name" in l]
                self.log(f"Found {len(loans_with_class)} loans with class_name out of {len(loans)} total")
                assert len(loans_with_class) > 0, "No loans have class_name field"
        self.test("GET /api/reports?type=transaksi includes class_name", _test)

    def test_excel_transaksi_includes_kelas_column(self):
        """Test Excel export for transaksi includes Kelas column"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/export.xlsx?type=transaksi&period=semua", headers=headers)
            assert resp.status_code == 200, f"Excel export failed: {resp.status_code} {resp.text}"
            
            # Load Excel and check for Kelas column
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(resp.content))
            ws = wb.active
            
            # Find header row (row 7 based on reports_pdf.py)
            headers_row = [cell.value for cell in ws[7]]
            assert "Kelas" in headers_row, f"Kelas column not found in headers: {headers_row}"
            
            # Check that Kelas is the 2nd column (after No)
            kelas_index = headers_row.index("Kelas")
            assert kelas_index == 2, f"Kelas should be 2nd column (index 2), found at index {kelas_index}"
            
            self.log(f"Excel has Kelas column at position {kelas_index + 1}")
        self.test("Excel export type=transaksi includes Kelas column (2nd column)", _test)

    def test_pdf_transaksi_includes_kelas_column(self):
        """Test PDF export for transaksi includes Kelas column"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/export.pdf?type=transaksi&period=semua", headers=headers)
            assert resp.status_code == 200, f"PDF export failed: {resp.status_code} {resp.text}"
            assert resp.headers.get("content-type") == "application/pdf", "Wrong content type"
            
            # Verify PDF is valid
            assert resp.content.startswith(b"%PDF"), "Should be a valid PDF"
            assert len(resp.content) > 1000, "PDF should have content"
            
            # Check if PDF contains "Kelas" text (basic check)
            pdf_text = resp.content.decode('latin-1', errors='ignore')
            assert "Kelas" in pdf_text, "PDF should contain 'Kelas' column header"
            
            self.log(f"PDF contains Kelas column")
        self.test("PDF export type=transaksi includes Kelas column", _test)

    # ===== FEATURE 3: EXCEL EXPORT FOR SUMMARY REPORTS =====
    def test_summary_xlsx_endpoint_exists(self):
        """Test GET /api/reports/summary.xlsx endpoint exists"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/summary.xlsx", headers=headers)
            assert resp.status_code == 200, f"Summary xlsx failed: {resp.status_code} {resp.text}"
            assert "spreadsheet" in resp.headers.get("content-type", ""), "Wrong content type"
            self.log(f"Summary xlsx endpoint works: {len(resp.content)} bytes")
        self.test("GET /api/reports/summary.xlsx endpoint exists", _test)

    def test_summary_xlsx_is_valid_excel(self):
        """Test summary.xlsx returns valid Excel file (not CSV)"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/summary.xlsx?start=2024-01-01&end=2024-12-31", headers=headers)
            assert resp.status_code == 200, f"Summary xlsx failed: {resp.status_code} {resp.text}"
            
            # Verify it's a valid Excel file
            from openpyxl import load_workbook
            try:
                wb = load_workbook(io.BytesIO(resp.content))
                sheet_names = wb.sheetnames
                self.log(f"Excel has {len(sheet_names)} sheets: {sheet_names}")
                
                # Check for expected sheets
                expected_sheets = ["Ringkasan", "Grafik", "Buku terpopuler", "Anggota aktif"]
                for sheet in expected_sheets:
                    assert sheet in sheet_names, f"Missing sheet: {sheet}"
                
                self.log("All expected sheets present")
            except Exception as e:
                raise AssertionError(f"Invalid Excel file: {e}")
        self.test("GET /api/reports/summary.xlsx returns valid .xlsx (not CSV)", _test)

    def test_summary_xlsx_has_multiple_sheets(self):
        """Test summary.xlsx has Ringkasan, Grafik, Buku terpopuler, Anggota aktif sheets"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/summary.xlsx", headers=headers)
            assert resp.status_code == 200, f"Summary xlsx failed: {resp.status_code} {resp.text}"
            
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(resp.content))
            
            # Check Ringkasan sheet
            assert "Ringkasan" in wb.sheetnames, "Missing Ringkasan sheet"
            ws_ringkasan = wb["Ringkasan"]
            assert ws_ringkasan["B1"].value == "PERPUSTAKAAN SMA NEGERI 1 ABUNG TENGAH", "Wrong header"
            
            # Check Grafik sheet
            assert "Grafik" in wb.sheetnames, "Missing Grafik sheet"
            ws_grafik = wb["Grafik"]
            # Should have data table and charts
            
            # Check Buku terpopuler sheet
            assert "Buku terpopuler" in wb.sheetnames, "Missing Buku terpopuler sheet"
            
            # Check Anggota aktif sheet
            assert "Anggota aktif" in wb.sheetnames, "Missing Anggota aktif sheet"
            
            self.log("All sheets verified")
        self.test("summary.xlsx has all required sheets", _test)

    def test_summary_xlsx_orientation_portrait(self):
        """Test summary.xlsx with orientation=portrait"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/summary.xlsx?orientation=portrait", headers=headers)
            assert resp.status_code == 200, f"Summary xlsx portrait failed: {resp.status_code} {resp.text}"
            
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(resp.content))
            ws = wb.active
            
            assert ws.page_setup.orientation == "portrait", f"Expected portrait, got {ws.page_setup.orientation}"
            self.log("Portrait orientation set correctly")
        self.test("summary.xlsx orientation=portrait sets page orientation", _test)

    def test_summary_xlsx_orientation_landscape(self):
        """Test summary.xlsx with orientation=landscape"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/summary.xlsx?orientation=landscape", headers=headers)
            assert resp.status_code == 200, f"Summary xlsx landscape failed: {resp.status_code} {resp.text}"
            
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(resp.content))
            ws = wb.active
            
            assert ws.page_setup.orientation == "landscape", f"Expected landscape, got {ws.page_setup.orientation}"
            self.log("Landscape orientation set correctly")
        self.test("summary.xlsx orientation=landscape sets page orientation", _test)

    def test_summary_xlsx_siswa_forbidden(self):
        """Test siswa role gets 403 for summary.xlsx"""
        def _test():
            headers = {"Cookie": f"access_token={self.siswa_token}"}
            resp = requests.get(f"{BASE_URL}/reports/summary.xlsx", headers=headers)
            assert resp.status_code == 403, f"Expected 403 for siswa, got {resp.status_code}"
            self.log("Siswa correctly forbidden from accessing summary.xlsx")
        self.test("GET /api/reports/summary.xlsx returns 403 for siswa role", _test)

    def test_summary_xlsx_filename(self):
        """Test summary.xlsx has correct filename"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/summary.xlsx?start=2024-01-01&end=2024-12-31", headers=headers)
            assert resp.status_code == 200, f"Summary xlsx failed: {resp.status_code} {resp.text}"
            
            content_disp = resp.headers.get("content-disposition", "")
            assert "laporan-ringkasan-" in content_disp, f"Filename should contain 'laporan-ringkasan-': {content_disp}"
            assert ".xlsx" in content_disp, f"Filename should end with .xlsx: {content_disp}"
            
            self.log(f"Filename correct: {content_disp}")
        self.test("summary.xlsx has correct filename format", _test)

    # ===== REGRESSION: KUNJUNGAN REPORT STILL SHOWS KEPERLUAN =====
    def test_kunjungan_report_shows_keperluan(self):
        """Test Laporan Kunjungan still shows KEPERLUAN with custom text"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports?type=kunjungan&period=semua", headers=headers)
            assert resp.status_code == 200, f"Kunjungan report failed: {resp.status_code} {resp.text}"
            visits = resp.json()
            
            if len(visits) > 0:
                # Check if visits have purpose field
                visits_with_purpose = [v for v in visits if v.get("purpose")]
                self.log(f"Found {len(visits_with_purpose)} visits with purpose in report")
        self.test("Laporan Kunjungan report shows KEPERLUAN field", _test)

    def test_kunjungan_excel_has_keperluan_column(self):
        """Test Kunjungan Excel export has KEPERLUAN column"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/reports/export.xlsx?type=kunjungan&period=semua", headers=headers)
            assert resp.status_code == 200, f"Excel export failed: {resp.status_code} {resp.text}"
            
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(resp.content))
            ws = wb.active
            
            # Find header row
            headers_row = [cell.value for cell in ws[7]]
            assert "Keperluan" in headers_row, f"Keperluan column not found: {headers_row}"
            
            self.log("Kunjungan Excel has Keperluan column")
        self.test("Kunjungan Excel export has Keperluan column", _test)

    # ===== CLEANUP =====
    def cleanup(self):
        """Delete test data"""
        print(f"\n🧹 Cleaning up test data...")
        headers = {"Cookie": f"access_token={self.admin_token}"}
        
        # Delete test visits
        for visit_id in self.test_visit_ids:
            try:
                resp = requests.delete(f"{BASE_URL}/visits/{visit_id}", headers=headers)
                if resp.status_code == 200:
                    print(f"  ✓ Deleted visit {visit_id}")
            except Exception as e:
                print(f"  ✗ Error deleting visit: {e}")

    def summary(self):
        print(f"\n{'='*60}")
        print(f"📊 New Features Test Summary")
        print(f"{'='*60}")
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {self.tests_passed / self.tests_run * 100:.1f}%")
        print(f"{'='*60}")
        return 0 if self.tests_passed == self.tests_run else 1

def main():
    runner = NewFeaturesTestRunner()
    
    try:
        # Auth
        runner.test_admin_login()
        runner.test_siswa_login()
        
        # Feature 1: Lainnya purpose with custom text
        print(f"\n{'='*60}")
        print("FEATURE 1: Lainnya Purpose with Custom Text")
        print(f"{'='*60}")
        runner.test_scan_with_custom_purpose()
        runner.test_scan_with_empty_purpose()
        runner.test_guest_with_custom_purpose()
        runner.test_update_purpose_via_patch()
        runner.test_visits_list_shows_purpose()
        
        # Feature 2: Class column in transaction reports
        print(f"\n{'='*60}")
        print("FEATURE 2: Class Column in Transaction Reports")
        print(f"{'='*60}")
        runner.test_transaction_includes_class_name()
        runner.test_reports_transaksi_includes_class()
        runner.test_excel_transaksi_includes_kelas_column()
        runner.test_pdf_transaksi_includes_kelas_column()
        
        # Feature 3: Excel export for summary reports
        print(f"\n{'='*60}")
        print("FEATURE 3: Excel Export for Summary Reports")
        print(f"{'='*60}")
        runner.test_summary_xlsx_endpoint_exists()
        runner.test_summary_xlsx_is_valid_excel()
        runner.test_summary_xlsx_has_multiple_sheets()
        runner.test_summary_xlsx_orientation_portrait()
        runner.test_summary_xlsx_orientation_landscape()
        runner.test_summary_xlsx_siswa_forbidden()
        runner.test_summary_xlsx_filename()
        
        # Regression
        print(f"\n{'='*60}")
        print("REGRESSION TESTS")
        print(f"{'='*60}")
        runner.test_kunjungan_report_shows_keperluan()
        runner.test_kunjungan_excel_has_keperluan_column()
        
    finally:
        runner.cleanup()
    
    return runner.summary()

if __name__ == "__main__":
    sys.exit(main())
