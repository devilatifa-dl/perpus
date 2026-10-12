#!/usr/bin/env python3
"""
Backend API Test Suite for Perpustakaan App
Tests new/updated endpoints for member management, password changes, and portal separation
"""

import requests
import json
from typing import Dict, Optional

# Base URL from frontend/.env
BASE_URL = "https://perpus-library.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
CREDENTIALS = {
    "admin": {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"},
    "petugas": {"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"},
    "siswa": {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}
}

class TestSession:
    """Manages test session with authentication"""
    def __init__(self, role: str):
        self.role = role
        self.session = requests.Session()
        self.token = None
        self.user_data = None
        
    def login(self) -> bool:
        """Login and store token/cookies"""
        creds = CREDENTIALS[self.role]
        try:
            resp = self.session.post(f"{BASE_URL}/auth/login", json=creds)
            if resp.status_code == 200:
                data = resp.json()
                self.user_data = data
                # Token is in cookie (httponly) and also returned in response
                if "id" in data:
                    self.token = data.get("id")  # Store user id for reference
                    return True
            return False
        except Exception as e:
            print(f"Login error for {self.role}: {e}")
            return False
    
    def get(self, path: str) -> requests.Response:
        """GET request with auth"""
        return self.session.get(f"{BASE_URL}{path}")
    
    def post(self, path: str, json_data: dict) -> requests.Response:
        """POST request with auth"""
        return self.session.post(f"{BASE_URL}{path}", json=json_data)
    
    def put(self, path: str, json_data: dict) -> requests.Response:
        """PUT request with auth"""
        return self.session.put(f"{BASE_URL}{path}", json=json_data)
    
    def delete(self, path: str) -> requests.Response:
        """DELETE request with auth"""
        return self.session.delete(f"{BASE_URL}{path}")

def print_test(name: str):
    """Print test name"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print('='*80)

def assert_status(resp: requests.Response, expected: int, test_name: str):
    """Assert response status code"""
    if resp.status_code == expected:
        print(f"✅ PASS: {test_name} (status {resp.status_code})")
        return True
    else:
        print(f"❌ FAIL: {test_name}")
        print(f"   Expected: {expected}, Got: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
        return False

def test_login_portal_separation():
    """Test 1: Login portal separation"""
    print_test("Login Portal Separation")
    
    results = []
    
    # Test 1a: siswa with portal=admin -> 403
    print("\n1a. Siswa attempting login via portal=admin (should be 403)")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "siswa@smansa.sch.id",
        "password": "siswa123",
        "portal": "admin"
    })
    results.append(assert_status(resp, 403, "Siswa cannot login via admin portal"))
    
    # Test 1b: admin with portal=siswa -> 403
    print("\n1b. Admin attempting login via portal=siswa (should be 403)")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@smansa.sch.id",
        "password": "admin123",
        "portal": "siswa"
    })
    results.append(assert_status(resp, 403, "Admin cannot login via siswa portal"))
    
    # Test 1c: petugas with portal=siswa -> 403
    print("\n1c. Petugas attempting login via portal=siswa (should be 403)")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "petugas@smansa.sch.id",
        "password": "petugas123",
        "portal": "siswa"
    })
    results.append(assert_status(resp, 403, "Petugas cannot login via siswa portal"))
    
    # Test 1d: admin with portal=admin -> 200
    print("\n1d. Admin login via portal=admin (should be 200)")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@smansa.sch.id",
        "password": "admin123",
        "portal": "admin"
    })
    results.append(assert_status(resp, 200, "Admin can login via admin portal"))
    
    # Test 1e: siswa with portal=siswa -> 200
    print("\n1e. Siswa login via portal=siswa (should be 200)")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "siswa@smansa.sch.id",
        "password": "siswa123",
        "portal": "siswa"
    })
    results.append(assert_status(resp, 200, "Siswa can login via siswa portal"))
    
    return all(results)

def test_member_crud():
    """Test 2: Member CRUD operations"""
    print_test("Member CRUD Operations")
    
    results = []
    
    # Setup: Login as petugas (staff)
    staff = TestSession("petugas")
    if not staff.login():
        print("❌ FAIL: Could not login as petugas")
        return False
    
    # Setup: Login as siswa
    siswa = TestSession("siswa")
    if not siswa.login():
        print("❌ FAIL: Could not login as siswa")
        return False
    
    # Test 2a: Create a test member
    print("\n2a. Create test member (should be 200)")
    member_data = {
        "name": "Test Member Alpha",
        "student_id": "99001",
        "class_name": "TEST CLASS A",
        "photo": ""
    }
    resp = staff.post("/members", member_data)
    if assert_status(resp, 200, "Create member"):
        created_member = resp.json()
        member_id = created_member.get("id")
        print(f"   Created member ID: {member_id}")
        results.append(True)
    else:
        print("❌ Cannot continue without member creation")
        return False
    
    # Test 2b: Update member name
    print("\n2b. Update member name (should be 200)")
    update_data = {
        "name": "Test Member Alpha Updated",
        "student_id": "99001",
        "class_name": "TEST CLASS A",
        "photo": ""
    }
    resp = staff.put(f"/members/{member_id}", update_data)
    if assert_status(resp, 200, "Update member"):
        updated = resp.json()
        if updated.get("name") == "Test Member Alpha Updated":
            print(f"   ✅ Name updated correctly: {updated.get('name')}")
            results.append(True)
        else:
            print(f"   ❌ Name not updated: {updated.get('name')}")
            results.append(False)
    else:
        results.append(False)
    
    # Test 2c: Verify update via GET
    print("\n2c. Verify member update via GET /members")
    resp = staff.get("/members")
    if resp.status_code == 200:
        members = resp.json()
        found = next((m for m in members if m.get("id") == member_id), None)
        if found and found.get("name") == "Test Member Alpha Updated":
            print(f"   ✅ Member found with updated name")
            results.append(True)
        else:
            print(f"   ❌ Member not found or name not updated")
            results.append(False)
    else:
        print(f"   ❌ GET /members failed: {resp.status_code}")
        results.append(False)
    
    # Test 2d: Update non-existent member -> 404
    print("\n2d. Update non-existent member (should be 404)")
    resp = staff.put("/members/MB-NONEXIST", update_data)
    results.append(assert_status(resp, 404, "Update non-existent member returns 404"))
    
    # Test 2e: Siswa trying to update member -> 403
    print("\n2e. Siswa attempting to update member (should be 403)")
    resp = siswa.put(f"/members/{member_id}", update_data)
    results.append(assert_status(resp, 403, "Siswa cannot update member"))
    
    # Test 2f: Delete member
    print("\n2f. Delete member (should be 200)")
    resp = staff.delete(f"/members/{member_id}")
    results.append(assert_status(resp, 200, "Delete member"))
    
    # Test 2g: Verify deletion
    print("\n2g. Verify member deleted")
    resp = staff.get("/members")
    if resp.status_code == 200:
        members = resp.json()
        found = next((m for m in members if m.get("id") == member_id), None)
        if not found:
            print(f"   ✅ Member successfully deleted")
            results.append(True)
        else:
            print(f"   ❌ Member still exists after deletion")
            results.append(False)
    else:
        results.append(False)
    
    # Test 2h: Delete same member again -> 404
    print("\n2h. Delete already deleted member (should be 404)")
    resp = staff.delete(f"/members/{member_id}")
    results.append(assert_status(resp, 404, "Delete non-existent member returns 404"))
    
    return all(results)

def test_bulk_delete():
    """Test 3: Bulk delete members by class"""
    print_test("Bulk Delete Members by Class")
    
    results = []
    
    # Setup: Login as petugas
    staff = TestSession("petugas")
    if not staff.login():
        print("❌ FAIL: Could not login as petugas")
        return False
    
    # Setup: Login as siswa
    siswa = TestSession("siswa")
    if not siswa.login():
        print("❌ FAIL: Could not login as siswa")
        return False
    
    # Test 3a: Create multiple members in unique class
    print("\n3a. Create 3 members in TEST KELAS Z")
    test_class = "TEST KELAS Z"
    member_ids = []
    
    for i in range(3):
        member_data = {
            "name": f"Test Student Z{i+1}",
            "student_id": f"99{100+i}",
            "class_name": test_class,
            "photo": ""
        }
        resp = staff.post("/members", member_data)
        if resp.status_code == 200:
            member_id = resp.json().get("id")
            member_ids.append(member_id)
            print(f"   Created member {i+1}: {member_id}")
        else:
            print(f"   ❌ Failed to create member {i+1}")
            return False
    
    results.append(len(member_ids) == 3)
    
    # Test 3b: Bulk delete the class
    print(f"\n3b. Bulk delete class '{test_class}' (should be 200)")
    resp = staff.post("/members/bulk-delete", {"class_name": test_class})
    if assert_status(resp, 200, "Bulk delete class"):
        data = resp.json()
        deleted_count = data.get("deleted")
        print(f"   Deleted count: {deleted_count}")
        if deleted_count == 3:
            print(f"   ✅ Correct number of members deleted")
            results.append(True)
        else:
            print(f"   ❌ Expected 3 deletions, got {deleted_count}")
            results.append(False)
    else:
        results.append(False)
    
    # Test 3c: Verify members are gone
    print("\n3c. Verify members are deleted")
    resp = staff.get("/members")
    if resp.status_code == 200:
        members = resp.json()
        remaining = [m for m in members if m.get("id") in member_ids]
        if len(remaining) == 0:
            print(f"   ✅ All members deleted successfully")
            results.append(True)
        else:
            print(f"   ❌ {len(remaining)} members still exist")
            results.append(False)
    else:
        results.append(False)
    
    # Test 3d: Bulk delete non-existent class -> 404
    print("\n3d. Bulk delete non-existent class (should be 404)")
    resp = staff.post("/members/bulk-delete", {"class_name": "NONEXISTENT CLASS XYZ"})
    results.append(assert_status(resp, 404, "Bulk delete empty class returns 404"))
    
    # Test 3e: Siswa trying bulk delete -> 403
    print("\n3e. Siswa attempting bulk delete (should be 403)")
    resp = siswa.post("/members/bulk-delete", {"class_name": "ANY CLASS"})
    results.append(assert_status(resp, 403, "Siswa cannot bulk delete"))
    
    return all(results)

def test_change_own_password():
    """Test 4: Change own password (staff only)"""
    print_test("Change Own Password")
    
    results = []
    
    # Setup: Login as petugas
    staff = TestSession("petugas")
    if not staff.login():
        print("❌ FAIL: Could not login as petugas")
        return False
    
    # Setup: Login as siswa
    siswa = TestSession("siswa")
    if not siswa.login():
        print("❌ FAIL: Could not login as siswa")
        return False
    
    # Test 4a: Wrong current password -> 400
    print("\n4a. Change password with wrong current password (should be 400)")
    resp = staff.post("/account/password", {
        "current_password": "wrongpassword",
        "new_password": "newpass123"
    })
    results.append(assert_status(resp, 400, "Wrong current password returns 400"))
    
    # Test 4b: New password too short -> 422
    print("\n4b. Change password with short new password (should be 422)")
    resp = staff.post("/account/password", {
        "current_password": "petugas123",
        "new_password": "short"
    })
    results.append(assert_status(resp, 422, "Short password returns 422"))
    
    # Test 4c: Correct password change -> 200
    print("\n4c. Change password correctly (should be 200)")
    new_password = "newpetugas456"
    resp = staff.post("/account/password", {
        "current_password": "petugas123",
        "new_password": new_password
    })
    results.append(assert_status(resp, 200, "Password change successful"))
    
    # Test 4d: Login with new password
    print("\n4d. Login with new password (should be 200)")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "petugas@smansa.sch.id",
        "password": new_password,
        "portal": "admin"
    })
    results.append(assert_status(resp, 200, "Login with new password works"))
    
    # Test 4e: RESTORE password back to original
    print("\n4e. RESTORE password back to petugas123")
    # Need to login again with new password
    staff2 = TestSession("petugas")
    # Temporarily update credentials
    CREDENTIALS["petugas"]["password"] = new_password
    if staff2.login():
        resp = staff2.post("/account/password", {
            "current_password": new_password,
            "new_password": "petugas123"
        })
        if assert_status(resp, 200, "Password restored to original"):
            print("   ✅ Password restored successfully")
            results.append(True)
        else:
            print("   ❌ CRITICAL: Failed to restore password!")
            results.append(False)
    else:
        print("   ❌ CRITICAL: Could not login to restore password!")
        results.append(False)
    
    # Restore credentials dict
    CREDENTIALS["petugas"]["password"] = "petugas123"
    
    # Test 4f: Siswa calling endpoint -> 403
    print("\n4f. Siswa attempting to change password (should be 403)")
    resp = siswa.post("/account/password", {
        "current_password": "siswa123",
        "new_password": "newsiswa456"
    })
    results.append(assert_status(resp, 403, "Siswa cannot change password via this endpoint"))
    
    return all(results)

def test_admin_user_management():
    """Test 5: Admin user management"""
    print_test("Admin User Management")
    
    results = []
    
    # Setup: Login as admin
    admin = TestSession("admin")
    if not admin.login():
        print("❌ FAIL: Could not login as admin")
        return False
    
    # Setup: Login as petugas
    petugas = TestSession("petugas")
    if not petugas.login():
        print("❌ FAIL: Could not login as petugas")
        return False
    
    # Setup: Login as siswa
    siswa = TestSession("siswa")
    if not siswa.login():
        print("❌ FAIL: Could not login as siswa")
        return False
    
    # Test 5a: GET /users as admin -> 200
    print("\n5a. GET /users as admin (should be 200)")
    resp = admin.get("/users")
    if assert_status(resp, 200, "Admin can list users"):
        users = resp.json()
        print(f"   Found {len(users)} users")
        
        # Check no password_hash field
        has_password_hash = any("password_hash" in u for u in users)
        if not has_password_hash:
            print(f"   ✅ No password_hash field in response")
            results.append(True)
        else:
            print(f"   ❌ password_hash field found in response!")
            results.append(False)
        
        # Find petugas user for later tests
        petugas_user = next((u for u in users if u.get("email") == "petugas@smansa.sch.id"), None)
        if petugas_user:
            petugas_id = petugas_user.get("id")
            print(f"   Found petugas user ID: {petugas_id}")
        else:
            print(f"   ❌ Could not find petugas user")
            return False
    else:
        results.append(False)
        return False
    
    # Test 5b: GET /users as petugas -> 403
    print("\n5b. GET /users as petugas (should be 403)")
    resp = petugas.get("/users")
    results.append(assert_status(resp, 403, "Petugas cannot list users"))
    
    # Test 5c: GET /users as siswa -> 403
    print("\n5c. GET /users as siswa (should be 403)")
    resp = siswa.get("/users")
    results.append(assert_status(resp, 403, "Siswa cannot list users"))
    
    # Test 5d: Admin set petugas password
    print("\n5d. Admin set petugas password (should be 200)")
    new_password = "temppetugas999"
    resp = admin.put(f"/users/{petugas_id}/password", {"new_password": new_password})
    results.append(assert_status(resp, 200, "Admin can set user password"))
    
    # Test 5e: Verify petugas can login with new password
    print("\n5e. Verify petugas can login with new password")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "petugas@smansa.sch.id",
        "password": new_password,
        "portal": "admin"
    })
    results.append(assert_status(resp, 200, "Petugas can login with new password"))
    
    # Test 5f: RESTORE petugas password
    print("\n5f. RESTORE petugas password back to petugas123")
    resp = admin.put(f"/users/{petugas_id}/password", {"new_password": "petugas123"})
    if assert_status(resp, 200, "Password restored"):
        print("   ✅ Petugas password restored successfully")
        results.append(True)
    else:
        print("   ❌ CRITICAL: Failed to restore petugas password!")
        results.append(False)
    
    # Test 5g: Petugas trying to set password -> 403
    print("\n5g. Petugas attempting to set user password (should be 403)")
    resp = petugas.put(f"/users/{petugas_id}/password", {"new_password": "anything"})
    results.append(assert_status(resp, 403, "Non-admin cannot set user password"))
    
    # Test 5h: Admin set password for non-existent user -> 404
    print("\n5h. Admin set password for non-existent user (should be 404)")
    resp = admin.put("/users/u-nonexistent/password", {"new_password": "anything123"})
    results.append(assert_status(resp, 404, "Set password for non-existent user returns 404"))
    
    return all(results)

def test_card_settings_new_fields():
    """Test 6: Card settings new fields"""
    print_test("Card Settings New Fields (PUT/GET /api/settings)")
    
    results = []
    
    # Setup: Login as admin
    admin = TestSession("admin")
    if not admin.login():
        print("❌ FAIL: Could not login as admin")
        return False
    
    # Setup: Login as siswa
    siswa = TestSession("siswa")
    if not siswa.login():
        print("❌ FAIL: Could not login as siswa")
        return False
    
    # Test 6a: PUT /api/settings with ALL fields including new ones
    print("\n6a. PUT /api/settings with all fields including new card fields (should be 200)")
    settings_data = {
        "school_logo": "",
        "library_logo": "",
        "card_theme": "book",
        "card_layout": "portrait",
        "card_show_qr": True,
        "card_show_address": True,
        "card_title": "KARTU ANGGOTA PERPUSTAKAAN",
        "card_font": "klasik",
        "card_school_spacing": 3.5,
        "card_logo_pos": "kanan",
        "card_photo_pos": "kanan",
        "card_qr_pos": "bawah"
    }
    resp = admin.put("/settings", settings_data)
    results.append(assert_status(resp, 200, "Admin can update settings with new fields"))
    
    # Test 6b: GET /api/settings and verify new fields
    print("\n6b. GET /api/settings and verify new fields are saved")
    resp = admin.get("/settings")
    if assert_status(resp, 200, "GET settings"):
        settings = resp.json()
        
        # Check each new field
        checks = [
            ("card_theme", "book"),
            ("card_font", "klasik"),
            ("card_school_spacing", 3.5),
            ("card_logo_pos", "kanan"),
            ("card_photo_pos", "kanan"),
            ("card_qr_pos", "bawah")
        ]
        
        all_correct = True
        for field, expected in checks:
            actual = settings.get(field)
            if actual == expected:
                print(f"   ✅ {field} = {actual}")
            else:
                print(f"   ❌ {field} = {actual} (expected {expected})")
                all_correct = False
        
        results.append(all_correct)
    else:
        results.append(False)
    
    # Test 6c: Siswa cannot PUT settings -> 403
    print("\n6c. Siswa attempting to PUT /api/settings (should be 403)")
    resp = siswa.put("/settings", settings_data)
    results.append(assert_status(resp, 403, "Siswa cannot update settings"))
    
    # Test 6d: Siswa CAN GET settings -> 200 (no staff_only on GET)
    print("\n6d. Siswa can GET /api/settings (should be 200)")
    resp = siswa.get("/settings")
    results.append(assert_status(resp, 200, "Siswa can read settings"))
    
    # Test 6e: RESTORE settings to defaults
    print("\n6e. RESTORE settings to defaults")
    default_settings = {
        "school_logo": "",
        "library_logo": "",
        "card_theme": "navy",
        "card_layout": "classic",
        "card_show_qr": True,
        "card_show_address": True,
        "card_title": "KARTU ANGGOTA PERPUSTAKAAN",
        "card_font": "modern",
        "card_school_spacing": 0,
        "card_logo_pos": "kiri",
        "card_photo_pos": "kiri",
        "card_qr_pos": "atas"
    }
    resp = admin.put("/settings", default_settings)
    if assert_status(resp, 200, "Settings restored to defaults"):
        print("   ✅ Settings restored successfully")
        results.append(True)
    else:
        print("   ❌ Failed to restore settings")
        results.append(False)
    
    return all(results)

def test_reset_data_endpoint():
    """Test 7: Reset data endpoint"""
    print_test("Reset Data Endpoint (POST /api/admin/reset-data)")
    
    results = []
    
    # Setup: Login as admin
    admin = TestSession("admin")
    if not admin.login():
        print("❌ FAIL: Could not login as admin")
        return False
    
    # Setup: Login as petugas
    petugas = TestSession("petugas")
    if not petugas.login():
        print("❌ FAIL: Could not login as petugas")
        return False
    
    # Setup: Login as siswa
    siswa = TestSession("siswa")
    if not siswa.login():
        print("❌ FAIL: Could not login as siswa")
        return False
    
    # Test 7a: Petugas cannot reset -> 403
    print("\n7a. Petugas attempting POST /api/admin/reset-data (should be 403)")
    resp = petugas.post("/admin/reset-data", {"include_books": True})
    results.append(assert_status(resp, 403, "Petugas cannot reset data"))
    
    # Test 7b: Siswa cannot reset -> 403
    print("\n7b. Siswa attempting POST /api/admin/reset-data (should be 403)")
    resp = siswa.post("/admin/reset-data", {"include_books": True})
    results.append(assert_status(resp, 403, "Siswa cannot reset data"))
    
    # Test 7c: Admin can reset with include_books=true -> 200
    print("\n7c. Admin POST /api/admin/reset-data with include_books=true (should be 200)")
    resp = admin.post("/admin/reset-data", {"include_books": True})
    if assert_status(resp, 200, "Admin can reset data"):
        data = resp.json()
        
        # Check response structure
        if "ok" in data and data["ok"] == True:
            print(f"   ✅ Response has ok=true")
        else:
            print(f"   ❌ Response missing ok=true")
            results.append(False)
            return all(results)
        
        if "deleted" in data:
            deleted = data["deleted"]
            print(f"   ✅ Response has 'deleted' object:")
            print(f"      - members: {deleted.get('members', 'N/A')}")
            print(f"      - transactions: {deleted.get('transactions', 'N/A')}")
            print(f"      - incoming: {deleted.get('incoming', 'N/A')}")
            print(f"      - missing: {deleted.get('missing', 'N/A')}")
            print(f"      - reservations: {deleted.get('reservations', 'N/A')}")
            print(f"      - stocktake: {deleted.get('stocktake', 'N/A')}")
            print(f"      - books: {deleted.get('books', 'N/A')}")
            
            # All counts should be present (even if 0)
            required_keys = ["members", "transactions", "incoming", "missing", "reservations", "stocktake", "books"]
            has_all_keys = all(k in deleted for k in required_keys)
            if has_all_keys:
                print(f"   ✅ All required keys present in deleted object")
                results.append(True)
            else:
                print(f"   ❌ Missing keys in deleted object")
                results.append(False)
        else:
            print(f"   ❌ Response missing 'deleted' object")
            results.append(False)
    else:
        results.append(False)
    
    # Test 7d: Verify data is empty after reset
    print("\n7d. Verify data is empty after reset")
    
    # Check books
    resp = admin.get("/books")
    if resp.status_code == 200:
        books = resp.json()
        if len(books) == 0:
            print(f"   ✅ Books collection is empty (length=0)")
            results.append(True)
        else:
            print(f"   ❌ Books collection not empty (length={len(books)})")
            results.append(False)
    else:
        print(f"   ❌ Failed to GET /books")
        results.append(False)
    
    # Check members
    resp = admin.get("/members")
    if resp.status_code == 200:
        members = resp.json()
        if len(members) == 0:
            print(f"   ✅ Members collection is empty (length=0)")
            results.append(True)
        else:
            print(f"   ❌ Members collection not empty (length={len(members)})")
            results.append(False)
    else:
        print(f"   ❌ Failed to GET /members")
        results.append(False)
    
    # Check transactions
    resp = admin.get("/transactions")
    if resp.status_code == 200:
        transactions = resp.json()
        if len(transactions) == 0:
            print(f"   ✅ Transactions collection is empty (length=0)")
            results.append(True)
        else:
            print(f"   ❌ Transactions collection not empty (length={len(transactions)})")
            results.append(False)
    else:
        print(f"   ❌ Failed to GET /transactions")
        results.append(False)
    
    return all(results)

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PERPUSTAKAAN BACKEND API TEST SUITE - ROUND 2")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Testing with credentials from /app/memory/test_credentials.md")
    print("="*80)
    
    test_results = {}
    
    # Run round-2 tests (and regression test for login portal separation)
    test_results["Card Settings New Fields"] = test_card_settings_new_fields()
    test_results["Reset Data Endpoint"] = test_reset_data_endpoint()
    test_results["Login Portal Separation (Regression)"] = test_login_portal_separation()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(test_results)
    passed = sum(1 for p in test_results.values() if p)
    
    print("\n" + "="*80)
    print(f"TOTAL: {passed}/{total} test suites passed")
    print("="*80)
    
    return all(test_results.values())

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
