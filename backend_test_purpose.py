#!/usr/bin/env python3
"""
Backend API Testing for Visitor Purpose Feature
Tests purpose field in visitor check-in, editing, and reports
"""

import requests
import sys
from datetime import datetime

BASE_URL = "https://restore-app-34--3g9ynt9t.preview.emergentagent.com/api"

class PurposeTestRunner:
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

    def headers(self, token):
        return {"Cookie": f"access_token={token}"}

    # ===== SETUP =====
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
            self.log(f"Admin logged in: {data['name']}")
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
            self.siswa_token = resp.cookies.get("access_token")
            self.log(f"Siswa logged in: {data['name']}")
        self.test("Siswa login successful", _test)

    def test_get_member_24001(self):
        """Get member 24001 Bima Pratama"""
        def _test():
            resp = requests.get(f"{BASE_URL}/members", headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Failed to get members: {resp.status_code}"
            members = resp.json()
            bima = next((m for m in members if m.get("student_id") == "24001"), None)
            assert bima is not None, "Member 24001 Bima Pratama not found"
            self.test_member_id = bima["id"]
            self.log(f"Found member: {bima['name']} ({bima['id']})")
        self.test("Get member 24001 Bima Pratama", _test)

    # ===== PURPOSE TESTS =====
    def test_scan_with_purpose_membaca(self):
        """Test member check-in with purpose 'Membaca'"""
        def _test():
            resp = requests.post(f"{BASE_URL}/visits/scan", 
                json={"code": "24001", "purpose": "Membaca"},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Scan failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["action"] == "masuk", f"Expected masuk, got {data.get('action')}"
            assert data["visit"]["purpose"] == "Membaca", f"Expected purpose 'Membaca', got {data['visit'].get('purpose')}"
            assert data["member"]["name"] == "Bima Pratama", f"Expected Bima Pratama, got {data['member'].get('name')}"
            self.test_visit_ids.append(data["visit"]["id"])
            self.log(f"Check-in successful: {data['visit']['id']} with purpose '{data['visit']['purpose']}'")
        self.test("Member check-in with purpose 'Membaca'", _test)

    def test_scan_within_30s_returns_sudah_masuk(self):
        """Test scanning same member within 30s returns sudah_masuk"""
        def _test():
            resp = requests.post(f"{BASE_URL}/visits/scan", 
                json={"code": "24001", "purpose": "Mengerjakan tugas"},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Scan failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["action"] == "sudah_masuk", f"Expected sudah_masuk, got {data.get('action')}"
            self.log(f"Correctly returned sudah_masuk within 30s")
        self.test("Second scan within 30s returns sudah_masuk", _test)

    def test_checkout_member(self):
        """Test member checkout (scan keluar)"""
        def _test():
            import time
            time.sleep(31)  # Wait 31 seconds to avoid cooldown
            resp = requests.post(f"{BASE_URL}/visits/scan", 
                json={"code": "24001", "purpose": "Lainnya"},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Checkout failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["action"] == "keluar", f"Expected keluar, got {data.get('action')}"
            self.log(f"Checkout successful: {data['visit']['id']}")
        self.test("Member checkout (scan keluar)", _test)

    def test_purpose_persists_after_checkout(self):
        """Test that purpose doesn't change after checkout"""
        def _test():
            resp = requests.get(f"{BASE_URL}/visits", 
                params={"date": datetime.now().strftime("%Y-%m-%d")},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Failed to get visits: {resp.status_code}"
            data = resp.json()
            visit = next((v for v in data["items"] if v["id"] == self.test_visit_ids[0]), None)
            assert visit is not None, f"Visit {self.test_visit_ids[0]} not found"
            assert visit["purpose"] == "Membaca", f"Purpose changed! Expected 'Membaca', got '{visit.get('purpose')}'"
            assert visit["check_out"] is not None, "Visit should have check_out time"
            self.log(f"Purpose correctly persisted as 'Membaca' after checkout")
        self.test("Purpose persists after checkout", _test)

    def test_checkin_with_different_purpose(self):
        """Test member check-in with different purpose"""
        def _test():
            resp = requests.post(f"{BASE_URL}/visits/scan", 
                json={"code": "24001", "purpose": "Meminjam / mengembalikan buku"},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Scan failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["action"] == "masuk", f"Expected masuk, got {data.get('action')}"
            assert data["visit"]["purpose"] == "Meminjam / mengembalikan buku", f"Expected purpose 'Meminjam / mengembalikan buku', got {data['visit'].get('purpose')}"
            self.test_visit_ids.append(data["visit"]["id"])
            self.log(f"Check-in with purpose '{data['visit']['purpose']}'")
        self.test("Member check-in with different purpose", _test)

    def test_patch_purpose(self):
        """Test PATCH /visits/{id}/purpose"""
        def _test():
            visit_id = self.test_visit_ids[-1]
            resp = requests.patch(f"{BASE_URL}/visits/{visit_id}/purpose",
                json={"purpose": "Mengerjakan tugas"},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"PATCH failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["purpose"] == "Mengerjakan tugas", f"Expected 'Mengerjakan tugas', got '{data.get('purpose')}'"
            self.log(f"Purpose updated to '{data['purpose']}'")
        self.test("PATCH /visits/{id}/purpose updates purpose", _test)

    def test_patch_purpose_persists(self):
        """Test that patched purpose persists after reload"""
        def _test():
            visit_id = self.test_visit_ids[-1]
            resp = requests.get(f"{BASE_URL}/visits", 
                params={"date": datetime.now().strftime("%Y-%m-%d")},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Failed to get visits: {resp.status_code}"
            data = resp.json()
            visit = next((v for v in data["items"] if v["id"] == visit_id), None)
            assert visit is not None, f"Visit {visit_id} not found"
            assert visit["purpose"] == "Mengerjakan tugas", f"Purpose not persisted! Expected 'Mengerjakan tugas', got '{visit.get('purpose')}'"
            self.log(f"Purpose correctly persisted after reload")
        self.test("Patched purpose persists after reload", _test)

    def test_patch_purpose_404_unknown_id(self):
        """Test PATCH /visits/{id}/purpose returns 404 for unknown id"""
        def _test():
            resp = requests.patch(f"{BASE_URL}/visits/VS-UNKNOWN/purpose",
                json={"purpose": "Test"},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
            self.log(f"Correctly returned 404 for unknown visit id")
        self.test("PATCH purpose returns 404 for unknown id", _test)

    def test_patch_purpose_403_siswa_role(self):
        """Test PATCH /visits/{id}/purpose returns 403 for siswa role"""
        def _test():
            visit_id = self.test_visit_ids[-1]
            resp = requests.patch(f"{BASE_URL}/visits/{visit_id}/purpose",
                json={"purpose": "Test"},
                headers=self.headers(self.siswa_token))
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            self.log(f"Correctly returned 403 for siswa role")
        self.test("PATCH purpose returns 403 for siswa role", _test)

    def test_guest_with_purpose(self):
        """Test guest check-in with purpose"""
        def _test():
            resp = requests.post(f"{BASE_URL}/visits/guest",
                json={"name": "Test Guest Purpose", "origin": "Test Origin", "purpose": "Kunjungan dinas"},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Guest check-in failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["purpose"] == "Kunjungan dinas", f"Expected 'Kunjungan dinas', got '{data.get('purpose')}'"
            self.test_visit_ids.append(data["id"])
            self.log(f"Guest check-in with purpose '{data['purpose']}'")
        self.test("Guest check-in with purpose", _test)

    def test_visitor_list_has_purpose_column(self):
        """Test visitor list includes purpose field"""
        def _test():
            resp = requests.get(f"{BASE_URL}/visits", 
                params={"date": datetime.now().strftime("%Y-%m-%d")},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Failed to get visits: {resp.status_code}"
            data = resp.json()
            assert len(data["items"]) > 0, "No visits found"
            for visit in data["items"]:
                assert "purpose" in visit, f"Visit {visit['id']} missing purpose field"
            self.log(f"All {len(data['items'])} visits have purpose field")
        self.test("Visitor list includes purpose field", _test)

    def test_laporan_pengunjung_has_purpose(self):
        """Test Laporan > Pengunjung includes purpose"""
        def _test():
            resp = requests.get(f"{BASE_URL}/visits/history",
                params={"period": "harian"},
                headers=self.headers(self.admin_token))
            assert resp.status_code == 200, f"Failed to get history: {resp.status_code}"
            visits = resp.json()
            assert len(visits) > 0, "No visits in history"
            for visit in visits:
                assert "purpose" in visit, f"Visit {visit['id']} missing purpose field in history"
            self.log(f"All {len(visits)} visits in history have purpose field")
        self.test("Laporan > Pengunjung includes purpose", _test)

    # ===== CLEANUP =====
    def cleanup_test_visits(self):
        """Delete all test visit records"""
        def _test():
            deleted = 0
            for visit_id in self.test_visit_ids:
                try:
                    resp = requests.delete(f"{BASE_URL}/visits/{visit_id}",
                        headers=self.headers(self.admin_token))
                    if resp.status_code == 200:
                        deleted += 1
                except Exception as e:
                    self.log(f"Failed to delete {visit_id}: {e}")
            self.log(f"Deleted {deleted}/{len(self.test_visit_ids)} test visits")
        self.test("Cleanup: Delete test visit records", _test)

    def cleanup_leftover_guests(self):
        """Delete leftover 'TEST Guest Migration' guests"""
        def _test():
            resp = requests.get(f"{BASE_URL}/visits", 
                params={"date": datetime.now().strftime("%Y-%m-%d")},
                headers=self.headers(self.admin_token))
            if resp.status_code != 200:
                self.log("Could not fetch visits for cleanup")
                return
            data = resp.json()
            deleted = 0
            for visit in data["items"]:
                if visit.get("kind") == "tamu" and "TEST Guest Migration" in visit.get("name", ""):
                    try:
                        resp = requests.delete(f"{BASE_URL}/visits/{visit['id']}",
                            headers=self.headers(self.admin_token))
                        if resp.status_code == 200:
                            deleted += 1
                    except Exception as e:
                        self.log(f"Failed to delete {visit['id']}: {e}")
            self.log(f"Deleted {deleted} 'TEST Guest Migration' visits")
        self.test("Cleanup: Delete 'TEST Guest Migration' guests", _test)

    def cleanup_bima_today_visit(self):
        """Delete today's Bima Pratama visit if present"""
        def _test():
            resp = requests.get(f"{BASE_URL}/visits", 
                params={"date": datetime.now().strftime("%Y-%m-%d")},
                headers=self.headers(self.admin_token))
            if resp.status_code != 200:
                self.log("Could not fetch visits for cleanup")
                return
            data = resp.json()
            deleted = 0
            for visit in data["items"]:
                if visit.get("name") == "Bima Pratama" and visit.get("student_id") == "24001":
                    # Only delete if it's not one of our test visits
                    if visit["id"] not in self.test_visit_ids:
                        try:
                            resp = requests.delete(f"{BASE_URL}/visits/{visit['id']}",
                                headers=self.headers(self.admin_token))
                            if resp.status_code == 200:
                                deleted += 1
                        except Exception as e:
                            self.log(f"Failed to delete {visit['id']}: {e}")
            self.log(f"Deleted {deleted} pre-existing Bima Pratama visits")
        self.test("Cleanup: Delete pre-existing Bima Pratama visits", _test)

    def run_all(self):
        """Run all tests"""
        print("=" * 60)
        print("VISITOR PURPOSE FEATURE - BACKEND API TESTS")
        print("=" * 60)

        # Setup
        self.test_admin_login()
        self.test_siswa_login()
        self.test_get_member_24001()

        # Purpose tests
        self.test_scan_with_purpose_membaca()
        self.test_scan_within_30s_returns_sudah_masuk()
        self.test_checkout_member()
        self.test_purpose_persists_after_checkout()
        self.test_checkin_with_different_purpose()
        self.test_patch_purpose()
        self.test_patch_purpose_persists()
        self.test_patch_purpose_404_unknown_id()
        self.test_patch_purpose_403_siswa_role()
        self.test_guest_with_purpose()
        self.test_visitor_list_has_purpose_column()
        self.test_laporan_pengunjung_has_purpose()

        # Cleanup
        self.cleanup_bima_today_visit()
        self.cleanup_leftover_guests()
        self.cleanup_test_visits()

        # Summary
        print("\n" + "=" * 60)
        print(f"📊 RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 60)
        
        return 0 if self.tests_passed == self.tests_run else 1

if __name__ == "__main__":
    runner = PurposeTestRunner()
    sys.exit(runner.run_all())
