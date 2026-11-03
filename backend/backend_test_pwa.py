#!/usr/bin/env python3
"""
Backend API Testing for PWA Feature
Tests that APIs used by PWA caching are working correctly
"""

import requests
import sys

BASE_URL = "https://perpus-devilatifa--369vmy1r.preview.emergentagent.com/api"

class PWABackendTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.siswa_token = None

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
            assert "token" in data, "No token in response"
            self.admin_token = data["token"]
            print(f"  Admin token: {self.admin_token[:20]}...")
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
            data = resp.json()
            assert "token" in data, "No token in response"
            self.siswa_token = data["token"]
            print(f"  Siswa token: {self.siswa_token[:20]}...")
        self.test("Siswa login", _test)

    def test_auth_me_admin(self):
        """Test /api/auth/me for admin"""
        def _test():
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            assert resp.status_code == 200, f"Auth me failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["role"] == "admin", f"Expected admin role, got {data.get('role')}"
            print(f"  Admin user: {data['name']}")
        self.test("GET /api/auth/me (admin)", _test)

    def test_auth_me_siswa(self):
        """Test /api/auth/me for siswa"""
        def _test():
            headers = {"Authorization": f"Bearer {self.siswa_token}"}
            resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            assert resp.status_code == 200, f"Auth me failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["role"] == "siswa", f"Expected siswa role, got {data.get('role')}"
            print(f"  Siswa user: {data['name']}")
        self.test("GET /api/auth/me (siswa)", _test)

    def test_books_list(self):
        """Test /api/books"""
        def _test():
            headers = {"Authorization": f"Bearer {self.siswa_token}"}
            resp = requests.get(f"{BASE_URL}/books", headers=headers)
            assert resp.status_code == 200, f"Books list failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert isinstance(data, list), "Expected list of books"
            print(f"  Found {len(data)} books")
        self.test("GET /api/books", _test)

    def test_shelves_list(self):
        """Test /api/shelves"""
        def _test():
            headers = {"Authorization": f"Bearer {self.siswa_token}"}
            resp = requests.get(f"{BASE_URL}/shelves", headers=headers)
            assert resp.status_code == 200, f"Shelves list failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert isinstance(data, list), "Expected list of shelves"
            print(f"  Found {len(data)} shelves")
        self.test("GET /api/shelves", _test)

    def test_settings(self):
        """Test /api/settings"""
        def _test():
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/settings", headers=headers)
            assert resp.status_code == 200, f"Settings failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert isinstance(data, dict), "Expected settings object"
            print(f"  Settings loaded: {len(data)} keys")
        self.test("GET /api/settings", _test)

    def test_dashboard(self):
        """Test /api/dashboard"""
        def _test():
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/dashboard", headers=headers)
            assert resp.status_code == 200, f"Dashboard failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert isinstance(data, dict), "Expected dashboard object"
            print(f"  Dashboard loaded")
        self.test("GET /api/dashboard", _test)

def main():
    print("=" * 60)
    print("PWA Backend API Testing")
    print("=" * 60)
    
    tester = PWABackendTester()
    
    # Run tests
    tester.test_admin_login()
    tester.test_siswa_login()
    
    if tester.admin_token:
        tester.test_auth_me_admin()
        tester.test_settings()
        tester.test_dashboard()
    
    if tester.siswa_token:
        tester.test_auth_me_siswa()
        tester.test_books_list()
        tester.test_shelves_list()
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print("=" * 60)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
