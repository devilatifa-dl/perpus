#!/usr/bin/env python3
"""
Backend API Testing for Student Photo Upload Feature Toggle
Tests:
1. GET /api/settings/student-photo (any logged-in user) -> {enabled, until, allow_replace, open, updated_by?}
2. PUT /api/settings/student-photo (staff only; siswa -> 403) body {enabled, until (ISO or ''), allow_replace}
3. until in the past -> open=false
4. Invalid until -> 400
5. POST /api/members/{id}/photo as siswa: when open=false -> 403; when allow_replace=false and member has photo -> 403
6. POST /api/account/photo as siswa also gated
7. Admin/petugas always allowed regardless of setting
"""

import requests
import sys
from datetime import datetime, timedelta, timezone

BASE_URL = "https://devilatifa-perpus.preview.emergentagent.com/api"

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.petugas_token = None
        self.siswa_token = None
        self.test_member_id = None
        self.original_config = None

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
            assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
            self.admin_token = resp.cookies.get("access_token")
            self.log(f"Admin logged in, token: {self.admin_token[:20]}...")
        self.test("Admin login", _test)

    def login_petugas(self):
        """Login as petugas and get token"""
        def _test():
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "petugas@smansa.sch.id",
                "password": "petugas123",
                "portal": "admin"
            })
            assert resp.status_code == 200, f"Petugas login failed: {resp.status_code} {resp.text}"
            self.petugas_token = resp.cookies.get("access_token")
            self.log(f"Petugas logged in, token: {self.petugas_token[:20]}...")
        self.test("Petugas login", _test)

    def login_siswa(self):
        """Login as siswa and get token"""
        def _test():
            resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": "siswa@smansa.sch.id",
                "password": "siswa123",
                "portal": "siswa"
            })
            assert resp.status_code == 200, f"Siswa login failed: {resp.status_code} {resp.text}"
            self.siswa_token = resp.cookies.get("access_token")
            self.log(f"Siswa logged in, token: {self.siswa_token[:20]}...")
        self.test("Siswa login", _test)

    def test_get_config_admin(self):
        """Test GET /api/settings/student-photo as admin"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.get(f"{BASE_URL}/settings/student-photo", headers=headers)
            assert resp.status_code == 200, f"GET config failed: {resp.status_code} {resp.text}"
            
            data = resp.json()
            assert "enabled" in data, "Missing 'enabled' field"
            assert "until" in data, "Missing 'until' field"
            assert "allow_replace" in data, "Missing 'allow_replace' field"
            assert "open" in data, "Missing 'open' field"
            
            self.original_config = data
            self.log(f"Config: enabled={data['enabled']}, until={data['until']}, allow_replace={data['allow_replace']}, open={data['open']}")
        self.test("GET /api/settings/student-photo (admin)", _test)

    def test_get_config_siswa(self):
        """Test GET /api/settings/student-photo as siswa (should work)"""
        def _test():
            headers = {"Cookie": f"access_token={self.siswa_token}"}
            resp = requests.get(f"{BASE_URL}/settings/student-photo", headers=headers)
            assert resp.status_code == 200, f"GET config as siswa failed: {resp.status_code} {resp.text}"
            
            data = resp.json()
            assert "enabled" in data, "Missing 'enabled' field"
            assert "open" in data, "Missing 'open' field"
            self.log(f"Siswa can read config: open={data['open']}")
        self.test("GET /api/settings/student-photo (siswa can read)", _test)

    def test_put_config_siswa_403(self):
        """Test PUT /api/settings/student-photo as siswa (should get 403)"""
        def _test():
            headers = {"Cookie": f"access_token={self.siswa_token}"}
            resp = requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": True,
                "until": "",
                "allow_replace": True
            })
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            self.log("Siswa correctly denied PUT access")
        self.test("PUT /api/settings/student-photo (siswa gets 403)", _test)

    def test_put_config_enable(self):
        """Test PUT /api/settings/student-photo to enable"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": True,
                "until": "",
                "allow_replace": True
            })
            assert resp.status_code == 200, f"PUT config failed: {resp.status_code} {resp.text}"
            
            data = resp.json()
            assert data["enabled"] == True, f"Expected enabled=True, got {data['enabled']}"
            assert data["open"] == True, f"Expected open=True, got {data['open']}"
            assert data["allow_replace"] == True, f"Expected allow_replace=True, got {data['allow_replace']}"
            self.log(f"Config updated: enabled={data['enabled']}, open={data['open']}")
        self.test("PUT /api/settings/student-photo (enable)", _test)

    def test_put_config_disable(self):
        """Test PUT /api/settings/student-photo to disable"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": False,
                "until": "",
                "allow_replace": True
            })
            assert resp.status_code == 200, f"PUT config failed: {resp.status_code} {resp.text}"
            
            data = resp.json()
            assert data["enabled"] == False, f"Expected enabled=False, got {data['enabled']}"
            assert data["open"] == False, f"Expected open=False, got {data['open']}"
            self.log(f"Config updated: enabled={data['enabled']}, open={data['open']}")
        self.test("PUT /api/settings/student-photo (disable)", _test)

    def test_put_config_with_future_until(self):
        """Test PUT /api/settings/student-photo with future until"""
        def _test():
            future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": True,
                "until": future,
                "allow_replace": True
            })
            assert resp.status_code == 200, f"PUT config failed: {resp.status_code} {resp.text}"
            
            data = resp.json()
            assert data["enabled"] == True, f"Expected enabled=True, got {data['enabled']}"
            assert data["open"] == True, f"Expected open=True (future until), got {data['open']}"
            assert data["until"] != "", "Expected until to be set"
            self.log(f"Config with future until: open={data['open']}, until={data['until']}")
        self.test("PUT /api/settings/student-photo (with future until)", _test)

    def test_put_config_with_past_until(self):
        """Test PUT /api/settings/student-photo with past until -> open=false"""
        def _test():
            past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": True,
                "until": past,
                "allow_replace": True
            })
            assert resp.status_code == 200, f"PUT config failed: {resp.status_code} {resp.text}"
            
            data = resp.json()
            assert data["enabled"] == True, f"Expected enabled=True, got {data['enabled']}"
            assert data["open"] == False, f"Expected open=False (past until), got {data['open']}"
            self.log(f"Config with past until: open={data['open']} (correctly closed)")
        self.test("PUT /api/settings/student-photo (past until -> open=false)", _test)

    def test_put_config_invalid_until(self):
        """Test PUT /api/settings/student-photo with invalid until -> 400"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": True,
                "until": "invalid-date",
                "allow_replace": True
            })
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
            error = resp.json().get("detail", "")
            assert "tidak valid" in error.lower() or "invalid" in error.lower(), f"Expected validation error, got: {error}"
            self.log(f"Invalid until correctly rejected: {error}")
        self.test("PUT /api/settings/student-photo (invalid until -> 400)", _test)

    def test_put_config_petugas(self):
        """Test PUT /api/settings/student-photo as petugas (should work)"""
        def _test():
            headers = {"Cookie": f"access_token={self.petugas_token}"}
            resp = requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": True,
                "until": "",
                "allow_replace": True
            })
            assert resp.status_code == 200, f"Petugas PUT failed: {resp.status_code} {resp.text}"
            self.log("Petugas can update config")
        self.test("PUT /api/settings/student-photo (petugas allowed)", _test)

    def create_test_member(self):
        """Create a test member for photo upload tests"""
        def _test():
            headers = {"Cookie": f"access_token={self.admin_token}"}
            resp = requests.post(f"{BASE_URL}/members", headers=headers, json={
                "name": "Test Photo Member",
                "student_id": "99999",
                "class_name": "X IPA 1",
                "photo": ""
            })
            assert resp.status_code == 200, f"Create member failed: {resp.status_code} {resp.text}"
            self.test_member_id = resp.json()["id"]
            self.log(f"Created test member: {self.test_member_id}")
        self.test("Create test member", _test)

    def test_post_member_photo_when_disabled(self):
        """Test POST /api/members/{id}/photo as siswa when disabled -> 403"""
        def _test():
            # First disable photo upload
            headers = {"Cookie": f"access_token={self.admin_token}"}
            requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": False,
                "until": "",
                "allow_replace": True
            })
            
            # Try to upload photo as siswa
            headers = {"Cookie": f"access_token={self.siswa_token}"}
            resp = requests.post(f"{BASE_URL}/members/{self.test_member_id}/photo", headers=headers, json={
                "photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            })
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            error = resp.json().get("detail", "")
            assert "ditutup" in error.lower() or "closed" in error.lower(), f"Expected 'ditutup' in error, got: {error}"
            self.log(f"Siswa correctly blocked when disabled: {error}")
        self.test("POST /api/members/{id}/photo (siswa blocked when disabled)", _test)

    def test_post_member_photo_when_enabled(self):
        """Test POST /api/members/{id}/photo as siswa when enabled -> 200"""
        def _test():
            # Enable photo upload
            headers = {"Cookie": f"access_token={self.admin_token}"}
            requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": True,
                "until": "",
                "allow_replace": True
            })
            
            # Upload photo as siswa
            headers = {"Cookie": f"access_token={self.siswa_token}"}
            resp = requests.post(f"{BASE_URL}/members/{self.test_member_id}/photo", headers=headers, json={
                "photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            })
            assert resp.status_code == 200, f"Upload photo failed: {resp.status_code} {resp.text}"
            data = resp.json()
            assert data["photo"] != "", "Photo should be set"
            self.log(f"Siswa successfully uploaded photo")
        self.test("POST /api/members/{id}/photo (siswa allowed when enabled)", _test)

    def test_post_member_photo_replace_blocked(self):
        """Test POST /api/members/{id}/photo as siswa when allow_replace=false and photo exists -> 403"""
        def _test():
            # Set allow_replace=false
            headers = {"Cookie": f"access_token={self.admin_token}"}
            requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": True,
                "until": "",
                "allow_replace": False
            })
            
            # Try to replace photo as siswa (member already has photo from previous test)
            headers = {"Cookie": f"access_token={self.siswa_token}"}
            resp = requests.post(f"{BASE_URL}/members/{self.test_member_id}/photo", headers=headers, json={
                "photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            })
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            error = resp.json().get("detail", "")
            assert "sudah ada" in error.lower() or "already" in error.lower(), f"Expected 'sudah ada' in error, got: {error}"
            self.log(f"Siswa correctly blocked from replacing photo: {error}")
        self.test("POST /api/members/{id}/photo (replace blocked when allow_replace=false)", _test)

    def test_post_member_photo_admin_always_allowed(self):
        """Test POST /api/members/{id}/photo as admin always allowed regardless of settings"""
        def _test():
            # Disable photo upload
            headers = {"Cookie": f"access_token={self.admin_token}"}
            requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": False,
                "until": "",
                "allow_replace": False
            })
            
            # Admin should still be able to upload
            resp = requests.post(f"{BASE_URL}/members/{self.test_member_id}/photo", headers=headers, json={
                "photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            })
            assert resp.status_code == 200, f"Admin upload failed: {resp.status_code} {resp.text}"
            self.log("Admin can upload photo regardless of settings")
        self.test("POST /api/members/{id}/photo (admin always allowed)", _test)

    def test_post_account_photo_when_disabled(self):
        """Test POST /api/account/photo as siswa when disabled -> 403"""
        def _test():
            # Disable photo upload
            headers = {"Cookie": f"access_token={self.admin_token}"}
            requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
                "enabled": False,
                "until": "",
                "allow_replace": True
            })
            
            # Try to upload own photo as siswa
            headers = {"Cookie": f"access_token={self.siswa_token}"}
            resp = requests.post(f"{BASE_URL}/account/photo", headers=headers, json={
                "photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            })
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            error = resp.json().get("detail", "")
            assert "ditutup" in error.lower() or "closed" in error.lower(), f"Expected 'ditutup' in error, got: {error}"
            self.log(f"Siswa correctly blocked from /account/photo when disabled: {error}")
        self.test("POST /api/account/photo (siswa blocked when disabled)", _test)

    def restore_config(self):
        """Restore original config"""
        if not self.original_config:
            # Set to default enabled state
            self.original_config = {"enabled": True, "until": "", "allow_replace": True}
        
        print(f"\n🔄 Restoring original config...")
        headers = {"Cookie": f"access_token={self.admin_token}"}
        resp = requests.put(f"{BASE_URL}/settings/student-photo", headers=headers, json={
            "enabled": True,
            "until": "",
            "allow_replace": True
        })
        if resp.status_code == 200:
            print(f"  ✓ Config restored to enabled=True, until='', allow_replace=True")
        else:
            print(f"  ✗ Failed to restore config: {resp.status_code}")

    def cleanup(self):
        """Delete test member"""
        if not self.test_member_id:
            return
        
        print(f"\n🧹 Cleaning up test member...")
        headers = {"Cookie": f"access_token={self.admin_token}"}
        try:
            resp = requests.delete(f"{BASE_URL}/members/{self.test_member_id}", headers=headers)
            if resp.status_code == 200:
                print(f"  ✓ Deleted {self.test_member_id}")
            else:
                print(f"  ✗ Failed to delete {self.test_member_id}: {resp.status_code}")
        except Exception as e:
            print(f"  ✗ Error deleting {self.test_member_id}: {e}")

    def summary(self):
        print(f"\n{'='*60}")
        print(f"📊 Test Summary - Student Photo Upload Feature")
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
        # Login
        runner.login_admin()
        runner.login_petugas()
        runner.login_siswa()
        
        # Test GET config
        runner.test_get_config_admin()
        runner.test_get_config_siswa()
        
        # Test PUT config
        runner.test_put_config_siswa_403()
        runner.test_put_config_enable()
        runner.test_put_config_disable()
        runner.test_put_config_with_future_until()
        runner.test_put_config_with_past_until()
        runner.test_put_config_invalid_until()
        runner.test_put_config_petugas()
        
        # Test photo upload
        runner.create_test_member()
        runner.test_post_member_photo_when_disabled()
        runner.test_post_member_photo_when_enabled()
        runner.test_post_member_photo_replace_blocked()
        runner.test_post_member_photo_admin_always_allowed()
        runner.test_post_account_photo_when_disabled()
        
    finally:
        # Always cleanup and restore
        runner.cleanup()
        runner.restore_config()
    
    return runner.summary()

if __name__ == "__main__":
    sys.exit(main())
