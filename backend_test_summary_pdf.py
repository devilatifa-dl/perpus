#!/usr/bin/env python3
"""
Backend API Testing for Summary PDF Download Feature
Tests the new /api/reports/summary.pdf endpoint
"""

import requests
import sys
from datetime import datetime, timedelta

BASE_URL = "https://restore-app-34--3g9ynt9t.preview.emergentagent.com/api"

class PDFTestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.siswa_token = None

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

    def get_cookies(self, token):
        """Get cookies dict with access_token"""
        return {"access_token": token} if token else {}

    # ===== AUTH TESTS =====
    def test_admin_login(self):
        """Test admin login"""
        def _test():
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "admin@smansa.sch.id",
                "password": "admin123",
                "portal": "admin"
            })
            assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["role"] == "admin", f"Expected admin role, got {data.get('role')}"
            self.admin_token = resp.cookies.get("access_token")
            self.log(f"Admin logged in: {data['name']}, token: {self.admin_token[:20]}...")
        self.test("Admin login successful", _test)

    def test_siswa_login(self):
        """Test siswa login"""
        def _test():
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "siswa@smansa.sch.id",
                "password": "siswa123",
                "portal": "siswa"
            })
            assert resp.status_code == 200, f"Siswa login failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["role"] == "siswa", f"Expected siswa role, got {data.get('role')}"
            self.siswa_token = resp.cookies.get("access_token")
            self.log(f"Siswa logged in: {data['name']}")
        self.test("Siswa login successful", _test)

    # ===== PDF DOWNLOAD TESTS =====
    def test_pdf_download_portrait_default(self):
        """Test PDF download with portrait orientation (default)"""
        def _test():
            today = datetime.now().date()
            start = (today - timedelta(days=29)).isoformat()
            end = today.isoformat()
            
            resp = requests.get(f"{BASE_URL}/reports/summary.pdf", 
                params={"start": start, "end": end, "group": "day", "orientation": "portrait"},
                cookies=self.get_cookies(self.admin_token))
            
            assert resp.status_code == 200, f"PDF download failed: {resp.status_code} {resp.text}"
            assert resp.headers.get("Content-Type") == "application/pdf", f"Wrong content type: {resp.headers.get('Content-Type')}"
            
            # Check filename in Content-Disposition header
            cd = resp.headers.get("Content-Disposition", "")
            assert "attachment" in cd, f"Missing attachment in Content-Disposition: {cd}"
            assert f"laporan-ringkasan-{start}-{end}-potret.pdf" in cd, f"Wrong filename in header: {cd}"
            
            # Check PDF content
            content = resp.content
            assert content.startswith(b"%PDF"), "Response is not a valid PDF"
            assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
            
            self.log(f"PDF downloaded: {len(content)} bytes, filename: laporan-ringkasan-{start}-{end}-potret.pdf")
        self.test("PDF download portrait orientation", _test)

    def test_pdf_download_landscape(self):
        """Test PDF download with landscape orientation"""
        def _test():
            today = datetime.now().date()
            start = (today - timedelta(days=6)).isoformat()
            end = today.isoformat()
            
            resp = requests.get(f"{BASE_URL}/reports/summary.pdf", 
                params={"start": start, "end": end, "group": "day", "orientation": "landscape"},
                cookies=self.get_cookies(self.admin_token))
            
            assert resp.status_code == 200, f"PDF download failed: {resp.status_code} {resp.text}"
            assert resp.headers.get("Content-Type") == "application/pdf", f"Wrong content type: {resp.headers.get('Content-Type')}"
            
            # Check filename
            cd = resp.headers.get("Content-Disposition", "")
            assert f"laporan-ringkasan-{start}-{end}-lanskap.pdf" in cd, f"Wrong filename for landscape: {cd}"
            
            # Check PDF content
            content = resp.content
            assert content.startswith(b"%PDF"), "Response is not a valid PDF"
            assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
            
            self.log(f"PDF downloaded: {len(content)} bytes, filename: laporan-ringkasan-{start}-{end}-lanskap.pdf")
        self.test("PDF download landscape orientation", _test)

    def test_pdf_download_group_month(self):
        """Test PDF download with group=month"""
        def _test():
            today = datetime.now().date()
            start = today.replace(day=1).isoformat()
            end = today.isoformat()
            
            resp = requests.get(f"{BASE_URL}/reports/summary.pdf", 
                params={"start": start, "end": end, "group": "month", "orientation": "portrait"},
                cookies=self.get_cookies(self.admin_token))
            
            assert resp.status_code == 200, f"PDF download with group=month failed: {resp.status_code} {resp.text}"
            assert resp.headers.get("Content-Type") == "application/pdf", f"Wrong content type: {resp.headers.get('Content-Type')}"
            
            content = resp.content
            assert content.startswith(b"%PDF"), "Response is not a valid PDF"
            
            self.log(f"PDF with group=month downloaded: {len(content)} bytes")
        self.test("PDF download with group=month", _test)

    def test_pdf_download_custom_date_range(self):
        """Test PDF download with custom date range"""
        def _test():
            today = datetime.now().date()
            start = (today - timedelta(days=90)).isoformat()
            end = today.isoformat()
            
            resp = requests.get(f"{BASE_URL}/reports/summary.pdf", 
                params={"start": start, "end": end, "group": "day", "orientation": "portrait"},
                cookies=self.get_cookies(self.admin_token))
            
            assert resp.status_code == 200, f"PDF download with custom range failed: {resp.status_code} {resp.text}"
            assert resp.headers.get("Content-Type") == "application/pdf", f"Wrong content type: {resp.headers.get('Content-Type')}"
            
            content = resp.content
            assert content.startswith(b"%PDF"), "Response is not a valid PDF"
            
            self.log(f"PDF with custom date range (90 days) downloaded: {len(content)} bytes")
        self.test("PDF download with custom date range", _test)

    def test_pdf_invalid_date_format(self):
        """Test PDF download with invalid date format returns 400"""
        def _test():
            resp = requests.get(f"{BASE_URL}/reports/summary.pdf", 
                params={"start": "invalid-date", "end": "2024-01-01", "group": "day", "orientation": "portrait"},
                cookies=self.get_cookies(self.admin_token))
            
            assert resp.status_code == 400, f"Expected 400 for invalid date, got {resp.status_code}"
            
            self.log(f"Invalid date correctly rejected with 400")
        self.test("PDF download with invalid date returns 400", _test)

    def test_pdf_siswa_role_forbidden(self):
        """Test PDF download with siswa role returns 403"""
        def _test():
            today = datetime.now().date()
            start = (today - timedelta(days=6)).isoformat()
            end = today.isoformat()
            
            resp = requests.get(f"{BASE_URL}/reports/summary.pdf", 
                params={"start": start, "end": end, "group": "day", "orientation": "portrait"},
                cookies=self.get_cookies(self.siswa_token))
            
            assert resp.status_code == 403, f"Expected 403 for siswa role, got {resp.status_code}"
            
            self.log(f"Siswa role correctly forbidden with 403")
        self.test("PDF download with siswa role returns 403", _test)

    def test_xlsx_still_works(self):
        """Test that Excel download still works"""
        def _test():
            today = datetime.now().date()
            start = (today - timedelta(days=6)).isoformat()
            end = today.isoformat()
            
            resp = requests.get(f"{BASE_URL}/reports/summary.xlsx", 
                params={"start": start, "end": end, "group": "day", "orientation": "landscape"},
                cookies=self.get_cookies(self.admin_token))
            
            assert resp.status_code == 200, f"Excel download failed: {resp.status_code} {resp.text}"
            assert "spreadsheetml" in resp.headers.get("Content-Type", ""), f"Wrong content type for Excel: {resp.headers.get('Content-Type')}"
            
            # Check filename
            cd = resp.headers.get("Content-Disposition", "")
            assert f"laporan-ringkasan-{start}-{end}.xlsx" in cd, f"Wrong filename for Excel: {cd}"
            
            content = resp.content
            assert len(content) > 1000, f"Excel file too small: {len(content)} bytes"
            
            self.log(f"Excel file downloaded: {len(content)} bytes")
        self.test("Excel download still works", _test)

    def test_summary_json_endpoint(self):
        """Test that JSON summary endpoint still works"""
        def _test():
            today = datetime.now().date()
            start = (today - timedelta(days=6)).isoformat()
            end = today.isoformat()
            
            resp = requests.get(f"{BASE_URL}/reports/summary", 
                params={"start": start, "end": end, "group": "day"},
                cookies=self.get_cookies(self.admin_token))
            
            assert resp.status_code == 200, f"Summary JSON failed: {resp.status_code} {resp.text}"
            data = resp.json()
            
            assert "kpis" in data, "Missing kpis in response"
            assert "series" in data, "Missing series in response"
            assert "top_books" in data, "Missing top_books in response"
            assert "top_members" in data, "Missing top_members in response"
            
            self.log(f"Summary JSON endpoint working: {len(data['series'])} data points")
        self.test("Summary JSON endpoint still works", _test)

    def run_all(self):
        """Run all tests"""
        print("=" * 60)
        print("BACKEND API TESTING: Summary PDF Download Feature")
        print("=" * 60)
        
        # Auth tests
        self.test_admin_login()
        self.test_siswa_login()
        
        # PDF download tests
        self.test_pdf_download_portrait_default()
        self.test_pdf_download_landscape()
        self.test_pdf_download_group_month()
        self.test_pdf_download_custom_date_range()
        self.test_pdf_invalid_date_format()
        self.test_pdf_siswa_role_forbidden()
        
        # Regression tests
        self.test_xlsx_still_works()
        self.test_summary_json_endpoint()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 60)
        
        return 0 if self.tests_passed == self.tests_run else 1

if __name__ == "__main__":
    runner = PDFTestRunner()
    sys.exit(runner.run_all())
