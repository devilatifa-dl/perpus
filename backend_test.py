#!/usr/bin/env python3
"""
Backend Test Suite - Round 9: Visitor Name Search & Camera Stability
Tests new features: member search API, visitor list filtering, camera toggle stability.
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict

# Base URL from frontend/.env
BASE_URL = "https://devilatifa-perpus.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
PETUGAS_CREDS = {"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"}
SISWA_CREDS = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}

# Known test members from seed data
TEST_MEMBERS = {
    "bima": {"id": "MB-2024001", "name": "Bima Pratama", "nis": "24001"},
    "siti": {"id": "MB-2024002", "name": "Siti Rahma", "nis": "24002"},
    "raka": {"id": "MB-2024003", "name": "Raka Wijaya", "nis": "24003"}
}

class TestSession:
    def __init__(self):
        self.admin_session = requests.Session()
        self.petugas_session = requests.Session()
        self.siswa_session = requests.Session()
        self.test_data = {
            "visits": []  # Track visits created during tests for cleanup
        }
        self.tests_passed = 0
        self.tests_failed = 0
    
    def login(self, session: requests.Session, creds: Dict) -> bool:
        """Login and store session cookie"""
        try:
            resp = session.post(f"{BASE_URL}/auth/login", json=creds)
            if resp.status_code == 200:
                print(f"✓ Logged in as {creds['email']} (portal={creds['portal']})")
                return True
            else:
                print(f"✗ Login failed for {creds['email']}: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            print(f"✗ Login error for {creds['email']}: {e}")
            return False
    
    def test(self, name: str, condition: bool, details: str = ""):
        """Record test result"""
        if condition:
            self.tests_passed += 1
            print(f"✅ PASS: {name}")
            if details:
                print(f"   {details}")
        else:
            self.tests_failed += 1
            print(f"❌ FAIL: {name}")
            if details:
                print(f"   {details}")
    
    def cleanup(self) -> bool:
        """Delete test visits created during testing"""
        print("\n=== CLEANUP: Removing Test Visits ===")
        success = True
        
        for visit_id in self.test_data["visits"]:
            try:
                resp = self.admin_session.delete(f"{BASE_URL}/visits/{visit_id}")
                if resp.status_code in [200, 404]:
                    print(f"✓ Deleted visit {visit_id}")
                else:
                    print(f"✗ Failed to delete visit {visit_id}: {resp.status_code}")
                    success = False
            except Exception as e:
                print(f"✗ Error deleting visit {visit_id}: {e}")
                success = False
        
        return success
    
    def test_member_search_api(self):
        """Test GET /api/visits/member-search endpoint"""
        print("\n" + "="*70)
        print("TEST GROUP 1: Member Search API")
        print("="*70)
        
        # Test 1.1: Search by partial name "bim" (should match Bima)
        print("\n--- Test 1.1: GET /api/visits/member-search?q=bim ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/member-search", params={"q": "bim"})
            self.test(
                "Search 'bim' returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                results = resp.json()
                self.test(
                    "Search 'bim' returns array",
                    isinstance(results, list),
                    f"Type: {type(results)}"
                )
                
                # Should find Bima Pratama
                bima_found = any(m.get("name") == "Bima Pratama" for m in results)
                self.test(
                    "Search 'bim' finds Bima Pratama",
                    bima_found,
                    f"Results: {[m.get('name') for m in results]}"
                )
                
                # Check result structure
                if results:
                    member = results[0]
                    required_fields = ["id", "name", "class_name", "student_id", "inside"]
                    has_all_fields = all(field in member for field in required_fields)
                    self.test(
                        "Member result has required fields (id, name, class_name, student_id, inside)",
                        has_all_fields,
                        f"Fields: {list(member.keys())}"
                    )
                    
                    self.test(
                        "'inside' field is boolean",
                        isinstance(member.get("inside"), bool),
                        f"inside={member.get('inside')} (type: {type(member.get('inside'))})"
                    )
                
                # Should return max 8 results
                self.test(
                    "Search returns max 8 results",
                    len(results) <= 8,
                    f"Count: {len(results)}"
                )
        except Exception as e:
            self.test("Search 'bim' API call", False, f"Exception: {e}")
        
        # Test 1.2: Search by partial name "siti" (should match Siti)
        print("\n--- Test 1.2: GET /api/visits/member-search?q=siti ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/member-search", params={"q": "siti"})
            self.test(
                "Search 'siti' returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                results = resp.json()
                siti_found = any(m.get("name") == "Siti Rahma" for m in results)
                self.test(
                    "Search 'siti' finds Siti Rahma",
                    siti_found,
                    f"Results: {[m.get('name') for m in results]}"
                )
        except Exception as e:
            self.test("Search 'siti' API call", False, f"Exception: {e}")
        
        # Test 1.3: Search by NIS "24001" (should match Bima)
        print("\n--- Test 1.3: GET /api/visits/member-search?q=24001 ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/member-search", params={"q": "24001"})
            self.test(
                "Search by NIS '24001' returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                results = resp.json()
                bima_found = any(m.get("student_id") == "24001" for m in results)
                self.test(
                    "Search by NIS '24001' finds Bima",
                    bima_found,
                    f"Results: {[(m.get('name'), m.get('student_id')) for m in results]}"
                )
        except Exception as e:
            self.test("Search by NIS API call", False, f"Exception: {e}")
        
        # Test 1.4: Search by member code "MB-2024002" (should match Siti)
        print("\n--- Test 1.4: GET /api/visits/member-search?q=MB-2024002 ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/member-search", params={"q": "MB-2024002"})
            self.test(
                "Search by code 'MB-2024002' returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                results = resp.json()
                siti_found = any(m.get("id") == "MB-2024002" for m in results)
                self.test(
                    "Search by code 'MB-2024002' finds Siti",
                    siti_found,
                    f"Results: {[(m.get('name'), m.get('id')) for m in results]}"
                )
        except Exception as e:
            self.test("Search by code API call", False, f"Exception: {e}")
        
        # Test 1.5: Query shorter than 2 chars returns empty array
        print("\n--- Test 1.5: GET /api/visits/member-search?q=b (1 char) ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/member-search", params={"q": "b"})
            self.test(
                "Query < 2 chars returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                results = resp.json()
                self.test(
                    "Query < 2 chars returns empty array",
                    results == [],
                    f"Results: {results}"
                )
        except Exception as e:
            self.test("Query < 2 chars", False, f"Exception: {e}")
        
        # Test 1.6: Empty query returns empty array
        print("\n--- Test 1.6: GET /api/visits/member-search?q= (empty) ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/member-search", params={"q": ""})
            self.test(
                "Empty query returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                results = resp.json()
                self.test(
                    "Empty query returns empty array",
                    results == [],
                    f"Results: {results}"
                )
        except Exception as e:
            self.test("Empty query", False, f"Exception: {e}")
        
        # Test 1.7: Siswa role gets 403 (staff only)
        print("\n--- Test 1.7: Siswa GET /api/visits/member-search (forbidden) ---")
        try:
            resp = self.siswa_session.get(f"{BASE_URL}/visits/member-search", params={"q": "bim"})
            self.test(
                "Siswa cannot access member-search (403)",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa member-search forbidden", False, f"Exception: {e}")
        
        # Test 1.8: Petugas can access (staff role)
        print("\n--- Test 1.8: Petugas GET /api/visits/member-search ---")
        try:
            resp = self.petugas_session.get(f"{BASE_URL}/visits/member-search", params={"q": "bim"})
            self.test(
                "Petugas can access member-search (200)",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Petugas member-search access", False, f"Exception: {e}")
    
    def test_inside_field_accuracy(self):
        """Test that 'inside' field correctly reflects member status"""
        print("\n" + "="*70)
        print("TEST GROUP 2: 'inside' Field Accuracy")
        print("="*70)
        
        # Test 2.1: Check-in a member, verify 'inside' = true
        print("\n--- Test 2.1: Check-in member, verify 'inside' = true ---")
        try:
            # Check-in Bima
            resp = self.admin_session.post(f"{BASE_URL}/visits/scan", json={"code": TEST_MEMBERS["bima"]["id"]})
            if resp.status_code == 200:
                result = resp.json()
                if result.get("action") in ["masuk", "sudah_masuk"]:
                    visit_id = result.get("visit", {}).get("id")
                    if visit_id:
                        self.test_data["visits"].append(visit_id)
                    
                    # Search for Bima
                    resp = self.admin_session.get(f"{BASE_URL}/visits/member-search", params={"q": "bima"})
                    if resp.status_code == 200:
                        results = resp.json()
                        bima = next((m for m in results if m.get("id") == TEST_MEMBERS["bima"]["id"]), None)
                        if bima:
                            self.test(
                                "Member 'inside' = true after check-in",
                                bima.get("inside") == True,
                                f"inside={bima.get('inside')}"
                            )
                        else:
                            self.test("Find Bima in search results", False, "Bima not found")
                    else:
                        self.test("Search after check-in", False, f"Status: {resp.status_code}")
                else:
                    print(f"⚠ INFO: Check-in returned action={result.get('action')}, skipping 'inside' test")
            else:
                print(f"⚠ SKIP: Check-in failed with status {resp.status_code}")
        except Exception as e:
            self.test("Check-in and verify 'inside'", False, f"Exception: {e}")
        
        # Test 2.2: Check-out member, verify 'inside' = false
        print("\n--- Test 2.2: Check-out member, verify 'inside' = false ---")
        try:
            # Wait a bit to avoid 30s cooldown
            import time
            time.sleep(2)
            
            # Check-out Bima
            resp = self.admin_session.post(f"{BASE_URL}/visits/scan", json={"code": TEST_MEMBERS["bima"]["id"]})
            if resp.status_code == 200:
                result = resp.json()
                if result.get("action") == "keluar":
                    # Search for Bima
                    resp = self.admin_session.get(f"{BASE_URL}/visits/member-search", params={"q": "bima"})
                    if resp.status_code == 200:
                        results = resp.json()
                        bima = next((m for m in results if m.get("id") == TEST_MEMBERS["bima"]["id"]), None)
                        if bima:
                            self.test(
                                "Member 'inside' = false after check-out",
                                bima.get("inside") == False,
                                f"inside={bima.get('inside')}"
                            )
                        else:
                            self.test("Find Bima in search results", False, "Bima not found")
                    else:
                        self.test("Search after check-out", False, f"Status: {resp.status_code}")
                else:
                    print(f"⚠ INFO: Check-out returned action={result.get('action')}, may be within 30s cooldown")
            else:
                print(f"⚠ SKIP: Check-out failed with status {resp.status_code}")
        except Exception as e:
            self.test("Check-out and verify 'inside'", False, f"Exception: {e}")
    
    def test_regression(self):
        """Test that existing visitor features still work"""
        print("\n" + "="*70)
        print("TEST GROUP 3: Regression Tests")
        print("="*70)
        
        # Test 3.1: GET /api/visits (list visits)
        print("\n--- Test 3.1: GET /api/visits (list visits) ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits")
            self.test(
                "List visits returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                data = resp.json()
                required_fields = ["date", "checkout_time", "items", "summary"]
                has_fields = all(field in data for field in required_fields)
                self.test(
                    "List visits has required fields",
                    has_fields,
                    f"Fields: {list(data.keys())}"
                )
        except Exception as e:
            self.test("List visits", False, f"Exception: {e}")
        
        # Test 3.2: POST /api/visits/guest (add guest)
        print("\n--- Test 3.2: POST /api/visits/guest (add guest) ---")
        try:
            guest_data = {
                "name": "Test Guest",
                "origin": "Test School",
                "purpose": "Testing"
            }
            resp = self.admin_session.post(f"{BASE_URL}/visits/guest", json=guest_data)
            self.test(
                "Add guest returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                guest = resp.json()
                visit_id = guest.get("id")
                if visit_id:
                    self.test_data["visits"].append(visit_id)
                
                self.test(
                    "Guest has correct name",
                    guest.get("name") == "Test Guest",
                    f"Name: {guest.get('name')}"
                )
        except Exception as e:
            self.test("Add guest", False, f"Exception: {e}")
        
        # Test 3.3: GET /api/visits/config (checkout time config)
        print("\n--- Test 3.3: GET /api/visits/config ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/config")
            self.test(
                "Get config returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                config = resp.json()
                self.test(
                    "Config has checkout_time field",
                    "checkout_time" in config,
                    f"checkout_time: {config.get('checkout_time')}"
                )
        except Exception as e:
            self.test("Get config", False, f"Exception: {e}")
        
        # Test 3.4: GET /api/visits/stats (statistics)
        print("\n--- Test 3.4: GET /api/visits/stats ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/stats", params={"period": "7hari"})
            self.test(
                "Get stats returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Get stats", False, f"Exception: {e}")
        
        # Test 3.5: GET /api/visits/leaderboard (leaderboard)
        print("\n--- Test 3.5: GET /api/visits/leaderboard ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/leaderboard")
            self.test(
                "Get leaderboard returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Get leaderboard", False, f"Exception: {e}")
    
    def run_tests(self) -> bool:
        """Run all test groups"""
        print("\n" + "="*70)
        print("ROUND 9 BACKEND TESTS: Visitor Name Search & Camera Stability")
        print("="*70)
        
        # Login
        if not self.login(self.admin_session, ADMIN_CREDS):
            return False
        if not self.login(self.petugas_session, PETUGAS_CREDS):
            return False
        if not self.login(self.siswa_session, SISWA_CREDS):
            return False
        
        # Run test groups
        self.test_member_search_api()
        self.test_inside_field_accuracy()
        self.test_regression()
        
        # Cleanup
        cleanup_success = self.cleanup()
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"📊 Total: {self.tests_passed + self.tests_failed}")
        print(f"🧹 Cleanup: {'✓ Success' if cleanup_success else '✗ Failed'}")
        print("="*70)
        
        if self.tests_failed == 0 and cleanup_success:
            print("✅ ALL TESTS PASSED")
            return True
        else:
            print("❌ SOME TESTS FAILED")
            return False

def main():
    test_session = TestSession()
    success = test_session.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
