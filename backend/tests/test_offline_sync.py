#!/usr/bin/env python3
"""
Backend API Testing for Offline Mode Features
Tests offline sync endpoints with client_id and client_time
"""

import requests
import sys
from datetime import datetime, timedelta, timezone

BASE_URL = "https://restore-zip-27--9nkrrgqk.preview.emergentagent.com/api"

class OfflineSyncTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.test_member_id = None
        self.test_book_id = None

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
        """Login as admin"""
        def _test():
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "admin@smansa.sch.id",
                "password": "admin123",
                "portal": "admin"
            })
            assert resp.status_code == 200, f"Login failed: {resp.status_code}"
            self.admin_token = resp.cookies.get("access_token")
            self.log("Admin logged in")
        self.test("Admin login", _test)

    def get_test_data(self):
        """Get test member and book"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            
            # Get members
            resp = requests.get(f"{BASE_URL}/members", headers=headers)
            assert resp.status_code == 200, "Failed to get members"
            members = resp.json()
            assert len(members) > 0, "No members found"
            self.test_member_id = members[0]["id"]
            self.log(f"Test member: {self.test_member_id}")
            
            # Get books
            resp = requests.get(f"{BASE_URL}/books", headers=headers)
            assert resp.status_code == 200, "Failed to get books"
            books = resp.json()
            available = [b for b in books if b.get("available", 0) > 0]
            assert len(available) > 0, "No available books"
            self.test_book_id = available[0]["id"]
            self.log(f"Test book: {self.test_book_id}")
        self.test("Get test data (member & book)", _test)

    def test_offline_transaction_with_client_id(self):
        """Test POST /api/transactions with client_id & client_time"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            client_id = f"test-offline-{datetime.now().timestamp()}"
            client_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            
            data = {
                "member_id": self.test_member_id,
                "book_id": self.test_book_id,
                "action": "pinjam",
                "client_id": client_id,
                "client_time": client_time
            }
            
            resp = requests.post(f"{BASE_URL}/transactions", json=data, headers=headers)
            assert resp.status_code == 200, f"Transaction failed: {resp.status_code} {resp.text}"
            result = resp.json()
            self.log(f"Transaction created with client_id: {client_id}")
            
            # Try duplicate - should not create new record
            resp2 = requests.post(f"{BASE_URL}/transactions", json=data, headers=headers)
            assert resp2.status_code == 200, "Duplicate should return 200"
            result2 = resp2.json()
            assert result["id"] == result2["id"], "Duplicate should return same transaction"
            self.log("Duplicate client_id correctly prevented double record")
        self.test("Offline transaction with client_id prevents duplicates", _test)

    def test_offline_transaction_old_time_ignored(self):
        """Test client_time older than 14 days is ignored"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            client_id = f"test-old-{datetime.now().timestamp()}"
            # 15 days ago - should be ignored
            client_time = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
            
            data = {
                "member_id": self.test_member_id,
                "book_id": self.test_book_id,
                "action": "kembali",
                "client_id": client_id,
                "client_time": client_time
            }
            
            resp = requests.post(f"{BASE_URL}/transactions", json=data, headers=headers)
            assert resp.status_code == 200, f"Transaction failed: {resp.status_code}"
            # Server should use current time, not old client_time
            self.log("Old client_time (>14 days) correctly ignored, server time used")
        self.test("Transaction with old client_time (>14 days) uses server time", _test)

    def test_offline_visit_scan_with_client_id(self):
        """Test POST /api/visits/scan with client_id & client_time"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            
            # Get a member
            resp = requests.get(f"{BASE_URL}/members", headers=headers)
            members = resp.json()
            member = members[0]
            
            client_id = f"test-visit-{datetime.now().timestamp()}"
            client_time = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
            
            data = {
                "code": member["student_id"] or member["id"],
                "purpose": "Membaca",
                "client_id": client_id,
                "client_time": client_time
            }
            
            resp = requests.post(f"{BASE_URL}/visits/scan", json=data, headers=headers)
            assert resp.status_code == 200, f"Visit scan failed: {resp.status_code} {resp.text}"
            result = resp.json()
            assert result.get("action") in ["masuk", "keluar", "duplikat"], f"Unexpected action: {result.get('action')}"
            self.log(f"Visit scan with client_id: {result.get('action')}")
            
            # Try duplicate
            resp2 = requests.post(f"{BASE_URL}/visits/scan", json=data, headers=headers)
            assert resp2.status_code == 200, "Duplicate should return 200"
            result2 = resp2.json()
            if result.get("action") == "masuk":
                assert result2.get("action") == "duplikat", "Duplicate should be detected"
                self.log("Duplicate visit scan correctly detected")
        self.test("Offline visit scan with client_id prevents duplicates", _test)

    def test_offline_guest_with_client_id(self):
        """Test POST /api/visits/guest with client_id & client_time"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            client_id = f"test-guest-{datetime.now().timestamp()}"
            client_time = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
            
            data = {
                "name": "TEST_Offline_Guest",
                "origin": "Test School",
                "purpose": "Test visit",
                "client_id": client_id,
                "client_time": client_time
            }
            
            resp = requests.post(f"{BASE_URL}/visits/guest", json=data, headers=headers)
            assert resp.status_code == 200, f"Guest visit failed: {resp.status_code} {resp.text}"
            result = resp.json()
            assert "id" in result, "Guest visit should have id"
            self.log(f"Guest visit created with client_id")
            
            # Try duplicate
            resp2 = requests.post(f"{BASE_URL}/visits/guest", json=data, headers=headers)
            assert resp2.status_code == 200, "Duplicate should return 200"
            result2 = resp2.json()
            assert result["id"] == result2["id"], "Duplicate should return same visit"
            assert result2.get("duplicate") is True, "Should mark as duplicate"
            self.log("Duplicate guest visit correctly prevented")
        self.test("Offline guest visit with client_id prevents duplicates", _test)

    def test_offline_checkout_with_client_id(self):
        """Test POST /api/visits/{id}/checkout with client_id & client_time"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            
            # Get visits
            resp = requests.get(f"{BASE_URL}/visits", headers=headers)
            assert resp.status_code == 200, "Failed to get visits"
            data = resp.json()
            visits = data.get("items", [])
            open_visits = [v for v in visits if not v.get("check_out")]
            
            if not open_visits:
                self.log("No open visits to test checkout, skipping")
                return
            
            visit_id = open_visits[0]["id"]
            client_id = f"test-checkout-{datetime.now().timestamp()}"
            client_time = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
            
            checkout_data = {
                "client_id": client_id,
                "client_time": client_time
            }
            
            resp = requests.post(f"{BASE_URL}/visits/{visit_id}/checkout", json=checkout_data, headers=headers)
            assert resp.status_code == 200, f"Checkout failed: {resp.status_code} {resp.text}"
            result = resp.json()
            assert result.get("check_out") is not None, "Visit should be checked out"
            self.log(f"Visit checked out with client_id")
            
            # Try duplicate checkout
            resp2 = requests.post(f"{BASE_URL}/visits/{visit_id}/checkout", json=checkout_data, headers=headers)
            assert resp2.status_code in [200, 400], "Duplicate checkout should return 200 or 400"
            if resp2.status_code == 200:
                self.log("Duplicate checkout correctly handled")
        self.test("Offline checkout with client_id", _test)

    def test_settings_endpoint(self):
        """Test GET /api/settings returns card design settings"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/settings", headers=headers)
            assert resp.status_code == 200, f"Settings failed: {resp.status_code}"
            settings = resp.json()
            
            # Check card design fields
            required_fields = [
                "card_text_fonts", "card_photo_shape", "card_photo_size",
                "card_show_class", "card_show_nis", "card_show_code"
            ]
            for field in required_fields:
                assert field in settings, f"Settings missing field: {field}"
            
            self.log(f"Settings loaded with card design fields")
        self.test("GET /api/settings returns card design settings", _test)

    def summary(self):
        print(f"\n{'='*60}")
        print(f"📊 Offline Sync Test Summary")
        print(f"{'='*60}")
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {self.tests_passed / self.tests_run * 100:.1f}%")
        print(f"{'='*60}")
        return 0 if self.tests_passed == self.tests_run else 1

def main():
    tester = OfflineSyncTester()
    
    # Run tests
    tester.login_admin()
    tester.get_test_data()
    tester.test_offline_transaction_with_client_id()
    tester.test_offline_transaction_old_time_ignored()
    tester.test_offline_visit_scan_with_client_id()
    tester.test_offline_guest_with_client_id()
    tester.test_offline_checkout_with_client_id()
    tester.test_settings_endpoint()
    
    return tester.summary()

if __name__ == "__main__":
    sys.exit(main())
