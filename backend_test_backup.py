#!/usr/bin/env python3
"""Backend API tests for backup/restore with truncated ZIP handling and loan leaderboard"""
import requests
import sys
import json

BASE_URL = "https://perpus-devilatifa--369vmy1r.preview.emergentagent.com/api"

class BackupRestoreAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.admin_token = None
        self.petugas_token = None
        self.tests_run = 0
        self.tests_passed = 0

    def test(self, name, func):
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        try:
            func()
            self.tests_passed += 1
            print(f"✅ Passed")
            return True
        except AssertionError as e:
            print(f"❌ Failed - {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def login_admin(self):
        """Login as admin"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.status_code}"
        self.admin_token = response.json()["token"]
        print("✅ Admin login successful")

    def login_petugas(self):
        """Login as petugas"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"}
        )
        assert response.status_code == 200, f"Petugas login failed: {response.status_code}"
        self.petugas_token = response.json()["token"]
        print("✅ Petugas login successful")

    def test_backup_json(self):
        """Test GET /api/admin/backup (JSON) works"""
        response = requests.get(
            f"{self.base_url}/admin/backup",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "collections" in data, "Missing 'collections' in backup"
        assert "app" in data, "Missing 'app' in backup"
        print(f"  Backup JSON contains {len(data.get('collections', {}))} collections")

    def test_backup_zip(self):
        """Test GET /api/admin/backup.zip returns valid ZIP with loan leaderboard"""
        response = requests.get(
            f"{self.base_url}/admin/backup.zip",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check X-Backup-Bytes header
        expected_size = response.headers.get("x-backup-bytes")
        actual_size = len(response.content)
        assert expected_size, "Missing X-Backup-Bytes header"
        assert int(expected_size) == actual_size, f"Size mismatch: header={expected_size}, actual={actual_size}"
        print(f"  ZIP size: {actual_size} bytes, X-Backup-Bytes: {expected_size}")
        
        # Check ZIP contents
        import zipfile, io
        z = zipfile.ZipFile(io.BytesIO(response.content))
        names = z.namelist()
        
        # Check for data-cadangan.json
        assert any("data-cadangan.json" in n for n in names), "Missing data-cadangan.json"
        
        # Check for loan leaderboard reports
        loan_reports = [n for n in names if "06-Peringkat-Rajin-Meminjam" in n]
        assert len(loan_reports) > 0, "Missing loan leaderboard reports"
        
        pdf_reports = [n for n in loan_reports if n.endswith(".pdf")]
        xlsx_reports = [n for n in loan_reports if n.endswith(".xlsx")]
        assert len(pdf_reports) > 0, "Missing PDF loan leaderboard reports"
        assert len(xlsx_reports) > 0, "Missing XLSX loan leaderboard reports"
        print(f"  Found {len(loan_reports)} loan leaderboard reports ({len(pdf_reports)} PDF, {len(xlsx_reports)} XLSX)")
        
        # Check for visit leaderboard (existing feature)
        visit_reports = [n for n in names if "05-Peringkat-Rajin-Berkunjung" in n]
        assert len(visit_reports) > 0, "Missing visit leaderboard reports"
        print(f"  Found {len(visit_reports)} visit leaderboard reports")
        
        # Check BACA-SAYA.txt mentions loan leaderboard
        readme = z.read("BACA-SAYA.txt").decode("utf-8")
        assert "06-Peringkat-Rajin-Meminjam" in readme or "peringkat rajin meminjam" in readme.lower(), "BACA-SAYA.txt doesn't mention loan leaderboard"
        print(f"  BACA-SAYA.txt mentions loan leaderboard")

    def test_petugas_backup_forbidden(self):
        """Test petugas gets 403 on backup endpoints"""
        # Test backup JSON
        response = requests.get(
            f"{self.base_url}/admin/backup",
            headers={"Authorization": f"Bearer {self.petugas_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for petugas backup, got {response.status_code}"
        print(f"  Petugas correctly denied backup JSON access (403)")
        
        # Test backup ZIP
        response = requests.get(
            f"{self.base_url}/admin/backup.zip",
            headers={"Authorization": f"Bearer {self.petugas_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for petugas backup.zip, got {response.status_code}"
        print(f"  Petugas correctly denied backup ZIP access (403)")

    def test_petugas_restore_forbidden(self):
        """Test petugas gets 403 on restore endpoints"""
        response = requests.post(
            f"{self.base_url}/admin/restore/start",
            json={"filename": "test.zip", "size": 1000, "chunks": 1},
            headers={"Authorization": f"Bearer {self.petugas_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for petugas restore, got {response.status_code}"
        print(f"  Petugas correctly denied restore access (403)")

def main():
    tester = BackupRestoreAPITester()
    
    # Login
    print("=" * 60)
    print("BACKEND API TESTS - Backup/Restore & Loan Leaderboard")
    print("=" * 60)
    
    try:
        tester.login_admin()
        tester.login_petugas()
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return 1
    
    # Run tests
    tester.test("GET /api/admin/backup (JSON)", tester.test_backup_json)
    tester.test("GET /api/admin/backup.zip with loan leaderboard", tester.test_backup_zip)
    tester.test("Petugas 403 on backup endpoints", tester.test_petugas_backup_forbidden)
    tester.test("Petugas 403 on restore endpoints", tester.test_petugas_restore_forbidden)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print("=" * 60)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
