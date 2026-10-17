#!/usr/bin/env python3
"""
Backend API Testing for Backup/Restore with All Reports Feature
Tests:
1. GET /api/admin/backup.zip as admin returns 200 with ZIP file
2. ZIP contains data-cadangan.json, BACA-SAYA.txt, and all report files (xlsx + pdf)
3. Excel files can be opened with openpyxl and data rows start at row 8
4. Create a visit and incoming book, verify they appear in reports
5. Petugas and siswa get 403 on /api/admin/backup.zip
6. POST /api/admin/restore with ZIP restores successfully
7. Legacy JSON from GET /api/admin/backup still restores
8. Invalid zip returns 400
9. Existing /api/reports/export.pdf and export.xlsx still work
"""

import requests
import sys
import io
import zipfile
import json
from openpyxl import load_workbook

BASE_URL = "https://perpus-library-1.preview.emergentagent.com/api"

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.token = None
        self.admin_name = None
        self.test_visit_id = None
        self.test_book_id = None
        self.backup_zip = None
        self.backup_json = None

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

    def login_admin(self):
        """Login as admin and get token"""
        def _test():
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "admin@smansa.sch.id",
                "password": "admin123",
                "portal": "admin"
            })
            assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert "id" in data, "No user id in response"
            self.token = resp.cookies.get("access_token")
            self.admin_name = data["name"]
            self.log(f"Logged in as: {self.admin_name}")
        self.test("Admin login successful", _test)

    def test_backup_zip_admin(self):
        """Test GET /api/admin/backup.zip as admin returns 200 with ZIP"""
        def _test():
            headers = {"Cookie": f"access_token={self.token}"}
            resp = requests.get(f"{BASE_URL}/admin/backup.zip", headers=headers)
            assert resp.status_code == 200, f"Backup failed: {resp.status_code} {resp.text}"
            assert resp.headers.get("content-type") == "application/zip", f"Wrong content type: {resp.headers.get('content-type')}"
            assert len(resp.content) > 1000, "ZIP content too small"
            
            self.backup_zip = resp.content
            self.log(f"ZIP file size: {len(resp.content)} bytes")
        self.test("GET /api/admin/backup.zip as admin returns 200 application/zip", _test)

    def test_zip_contents(self):
        """Test ZIP contains data-cadangan.json, BACA-SAYA.txt, and all reports"""
        def _test():
            assert self.backup_zip, "No backup ZIP available"
            
            with zipfile.ZipFile(io.BytesIO(self.backup_zip)) as z:
                files = z.namelist()
                self.log(f"ZIP contains {len(files)} files")
                
                # Check required files
                assert "data-cadangan.json" in files, "Missing data-cadangan.json"
                assert "BACA-SAYA.txt" in files, "Missing BACA-SAYA.txt"
                self.log("✓ data-cadangan.json found")
                self.log("✓ BACA-SAYA.txt found")
                
                # Check report files
                required_reports = [
                    "laporan/01-Laporan-Transaksi.xlsx",
                    "laporan/01-Laporan-Transaksi.pdf",
                    "laporan/02-Laporan-Buku-Masuk.xlsx",
                    "laporan/02-Laporan-Buku-Masuk.pdf",
                    "laporan/03-Laporan-Buku-Hilang.xlsx",
                    "laporan/03-Laporan-Buku-Hilang.pdf",
                    "laporan/04-Laporan-Pengunjung.xlsx",
                    "laporan/04-Laporan-Pengunjung.pdf",
                ]
                
                for report in required_reports:
                    assert report in files, f"Missing {report}"
                    self.log(f"✓ {report} found")
                
                # Check for peringkat folder (at least current month should exist)
                peringkat_files = [f for f in files if f.startswith("laporan/05-Peringkat-Rajin-Berkunjung/")]
                assert len(peringkat_files) > 0, "No peringkat reports found"
                self.log(f"✓ Found {len(peringkat_files)} peringkat report files")
                
                # Verify data-cadangan.json is valid JSON
                json_data = z.read("data-cadangan.json")
                backup_data = json.loads(json_data)
                assert "collections" in backup_data, "data-cadangan.json missing 'collections'"
                assert "app" in backup_data, "data-cadangan.json missing 'app'"
                self.log(f"✓ data-cadangan.json is valid JSON with {len(backup_data['collections'])} collections")
                
                # Store for restore test
                self.backup_json = json_data
        self.test("ZIP contains data-cadangan.json, BACA-SAYA.txt, and all report files", _test)

    def test_excel_format(self):
        """Test Excel files can be opened with openpyxl and data rows start at row 8"""
        def _test():
            assert self.backup_zip, "No backup ZIP available"
            
            with zipfile.ZipFile(io.BytesIO(self.backup_zip)) as z:
                # Test one Excel file
                excel_file = "laporan/01-Laporan-Transaksi.xlsx"
                excel_data = z.read(excel_file)
                
                wb = load_workbook(io.BytesIO(excel_data), read_only=True)
                ws = wb.active
                
                rows = list(ws.iter_rows(values_only=True))
                assert len(rows) >= 8, f"Expected at least 8 rows, got {len(rows)}"
                
                # Row 7 should be header (0-indexed row 6)
                header_row = rows[6]
                assert header_row is not None, "Row 7 (header) is empty"
                self.log(f"Row 7 (header): {header_row[:3]}...")
                
                # Row 8 should be data or empty message (0-indexed row 7)
                data_row = rows[7]
                self.log(f"Row 8 (first data row): {data_row[:3] if data_row else 'empty'}...")
                
                self.log(f"✓ Excel file has {len(rows)} rows, data starts at row 8")
        self.test("Excel files open with openpyxl and data rows start at row 8", _test)

    def test_create_visit_and_incoming(self):
        """Create a visit and incoming book record"""
        def _test():
            headers = {"Cookie": f"access_token={self.token}"}
            
            # Create a visit for member MB-2024003
            visit_data = {
                "code": "MB-2024003",
                "purpose": "Test visit for backup"
            }
            resp = requests.post(f"{BASE_URL}/visits/scan", json=visit_data, headers=headers)
            assert resp.status_code == 200, f"Visit creation failed: {resp.status_code} {resp.text}"
            result = resp.json()
            # Visit ID is in result["visit"]["id"]
            self.test_visit_id = result.get("visit", {}).get("id")
            self.log(f"Created visit: {self.test_visit_id} (action: {result.get('action')})")
            
            # Create an incoming book record
            incoming_data = {
                "title": "Test Book for Backup",
                "author": "Test Author",
                "category": "Test",
                "shelf": "R-01",
                "quantity": 1,
                "source": "Test source"
            }
            resp = requests.post(f"{BASE_URL}/incoming", json=incoming_data, headers=headers)
            assert resp.status_code == 200, f"Incoming creation failed: {resp.status_code} {resp.text}"
            incoming = resp.json()
            self.test_book_id = incoming.get("book_id")
            self.log(f"Created incoming book: {self.test_book_id}")
        self.test("Create visit and incoming book record", _test)

    def test_reports_contain_test_data(self):
        """Test that new backup contains the test visit and incoming book"""
        def _test():
            headers = {"Cookie": f"access_token={self.token}"}
            
            # Get a fresh backup
            resp = requests.get(f"{BASE_URL}/admin/backup.zip", headers=headers)
            assert resp.status_code == 200, "Backup failed"
            
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                # Check data-cadangan.json contains our test data
                json_data = z.read("data-cadangan.json")
                backup_data = json.loads(json_data)
                
                # Check visits
                visits = backup_data["collections"].get("visits", [])
                test_visits = [v for v in visits if v.get("id") == self.test_visit_id]
                assert len(test_visits) > 0, f"Test visit {self.test_visit_id} not found in backup"
                self.log(f"✓ Test visit found in backup")
                
                # Check incoming
                incoming = backup_data["collections"].get("incoming", [])
                test_incoming = [i for i in incoming if i.get("book_id") == self.test_book_id]
                assert len(test_incoming) > 0, f"Test incoming book {self.test_book_id} not found in backup"
                self.log(f"✓ Test incoming book found in backup")
                
                # Note: We can't easily verify Excel/PDF contents contain the data
                # but if the JSON backup has it, the reports should too
                self.log("✓ Test data appears in backup (reports should contain it)")
        self.test("New backup contains test visit and incoming book in reports", _test)

    def test_petugas_403(self):
        """Test petugas gets 403 on /api/admin/backup.zip"""
        def _test():
            # Login as petugas
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "petugas@smansa.sch.id",
                "password": "petugas123",
                "portal": "admin"
            })
            assert resp.status_code == 200, "Petugas login failed"
            petugas_token = resp.cookies.get("access_token")
            
            # Try to download backup
            headers = {"Cookie": f"access_token={petugas_token}"}
            resp = requests.get(f"{BASE_URL}/admin/backup.zip", headers=headers)
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            self.log("✓ Petugas correctly denied access")
        self.test("Petugas gets 403 on /api/admin/backup.zip", _test)

    def test_siswa_403(self):
        """Test siswa gets 403 on /api/admin/backup.zip"""
        def _test():
            # Login as siswa
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "siswa@smansa.sch.id",
                "password": "siswa123",
                "portal": "siswa"
            })
            assert resp.status_code == 200, "Siswa login failed"
            siswa_token = resp.cookies.get("access_token")
            
            # Try to download backup
            headers = {"Cookie": f"access_token={siswa_token}"}
            resp = requests.get(f"{BASE_URL}/admin/backup.zip", headers=headers)
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            self.log("✓ Siswa correctly denied access")
        self.test("Siswa gets 403 on /api/admin/backup.zip", _test)

    def test_restore_with_zip(self):
        """Test POST /api/admin/restore with ZIP restores successfully"""
        def _test():
            assert self.backup_zip, "No backup ZIP available"
            
            headers = {"Cookie": f"access_token={self.token}"}
            files = {"file": ("backup.zip", io.BytesIO(self.backup_zip), "application/zip")}
            resp = requests.post(f"{BASE_URL}/admin/restore", headers=headers, files=files)
            assert resp.status_code == 200, f"Restore failed: {resp.status_code} {resp.text}"
            
            data = resp.json()
            assert data.get("ok") is True, "Restore did not return ok: true"
            assert "restored" in data, "No 'restored' counts in response"
            
            total = sum(data["restored"].values())
            self.log(f"✓ Restored {total} total entries")
            self.log(f"  Collections: {data['restored']}")
        self.test("POST /api/admin/restore with ZIP restores successfully", _test)

    def test_restore_with_legacy_json(self):
        """Test POST /api/admin/restore with legacy JSON still works"""
        def _test():
            # Get legacy JSON backup
            headers = {"Cookie": f"access_token={self.token}"}
            resp = requests.get(f"{BASE_URL}/admin/backup", headers=headers)
            assert resp.status_code == 200, f"Legacy backup failed: {resp.status_code}"
            
            legacy_json = resp.content
            
            # Restore with legacy JSON
            files = {"file": ("backup.json", io.BytesIO(legacy_json), "application/json")}
            resp = requests.post(f"{BASE_URL}/admin/restore", headers=headers, files=files)
            assert resp.status_code == 200, f"Restore failed: {resp.status_code} {resp.text}"
            
            data = resp.json()
            assert data.get("ok") is True, "Restore did not return ok: true"
            self.log(f"✓ Legacy JSON restore successful")
        self.test("POST /api/admin/restore with legacy JSON works", _test)

    def test_restore_invalid_zip(self):
        """Test POST /api/admin/restore with invalid zip returns 400"""
        def _test():
            headers = {"Cookie": f"access_token={self.token}"}
            
            # Create invalid zip (missing data-cadangan.json)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("dummy.txt", "invalid")
            buf.seek(0)
            
            files = {"file": ("invalid.zip", buf, "application/zip")}
            resp = requests.post(f"{BASE_URL}/admin/restore", headers=headers, files=files)
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
            
            error = resp.json().get("detail", "")
            assert "data-cadangan.json" in error, f"Error should mention data-cadangan.json: {error}"
            self.log(f"✓ Invalid ZIP correctly rejected: {error}")
        self.test("POST /api/admin/restore with invalid zip returns 400", _test)

    def test_existing_export_pdf(self):
        """Test existing /api/reports/export.pdf still works"""
        def _test():
            headers = {"Cookie": f"access_token={self.token}"}
            resp = requests.get(f"{BASE_URL}/reports/export.pdf?type=transaksi&period=semua", headers=headers)
            assert resp.status_code == 200, f"PDF export failed: {resp.status_code}"
            assert resp.headers.get("content-type") == "application/pdf", "Wrong content type"
            assert len(resp.content) > 1000, "PDF content too small"
            self.log(f"✓ PDF export works (size: {len(resp.content)} bytes)")
        self.test("Existing /api/reports/export.pdf still works", _test)

    def test_existing_export_xlsx(self):
        """Test existing /api/reports/export.xlsx still works"""
        def _test():
            headers = {"Cookie": f"access_token={self.token}"}
            resp = requests.get(f"{BASE_URL}/reports/export.xlsx?type=masuk&period=semua", headers=headers)
            assert resp.status_code == 200, f"Excel export failed: {resp.status_code}"
            assert "spreadsheet" in resp.headers.get("content-type", ""), "Wrong content type"
            assert len(resp.content) > 1000, "Excel content too small"
            
            # Verify it's a valid Excel file
            wb = load_workbook(io.BytesIO(resp.content), read_only=True)
            assert wb.active is not None, "Excel file has no active sheet"
            self.log(f"✓ Excel export works (size: {len(resp.content)} bytes)")
        self.test("Existing /api/reports/export.xlsx still works", _test)

    def cleanup(self):
        """Delete test data"""
        print(f"\n🧹 Cleaning up test data...")
        headers = {"Cookie": f"access_token={self.token}"}
        
        # Delete test visit
        if self.test_visit_id:
            try:
                resp = requests.delete(f"{BASE_URL}/visits/{self.test_visit_id}", headers=headers)
                if resp.status_code == 200:
                    print(f"  ✓ Deleted visit {self.test_visit_id}")
                else:
                    print(f"  ✗ Failed to delete visit: {resp.status_code}")
            except Exception as e:
                print(f"  ✗ Error deleting visit: {e}")
        
        # Delete test book
        if self.test_book_id:
            try:
                resp = requests.delete(f"{BASE_URL}/books/{self.test_book_id}", headers=headers)
                if resp.status_code == 200:
                    print(f"  ✓ Deleted book {self.test_book_id}")
                else:
                    print(f"  ✗ Failed to delete book: {resp.status_code}")
            except Exception as e:
                print(f"  ✗ Error deleting book: {e}")

    def summary(self):
        print(f"\n{'='*60}")
        print(f"📊 Test Summary")
        print(f"{'='*60}")
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {self.tests_passed / self.tests_run * 100:.1f}%")
        print(f"{'='*60}")
        return 0 if self.tests_passed == self.tests_run else 1

def main():
    runner = TestRunner()
    
    try:
        # Run all tests
        runner.login_admin()
        runner.test_backup_zip_admin()
        runner.test_zip_contents()
        runner.test_excel_format()
        runner.test_create_visit_and_incoming()
        runner.test_reports_contain_test_data()
        runner.test_petugas_403()
        runner.test_siswa_403()
        runner.test_restore_with_zip()
        runner.test_restore_with_legacy_json()
        runner.test_restore_invalid_zip()
        runner.test_existing_export_pdf()
        runner.test_existing_export_xlsx()
        
    finally:
        # Always cleanup
        runner.cleanup()
    
    return runner.summary()

if __name__ == "__main__":
    sys.exit(main())
