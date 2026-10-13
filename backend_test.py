#!/usr/bin/env python3
"""
Backend API Test Suite - Round 6
Tests for:
1. GET /api/members/options
2. POST /api/members/{member_id}/photo
3. POST /api/members/promote
"""

import requests
import json
import sys
import os

# Base URL from environment
BASE_URL = "https://perpus-app-6.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
PETUGAS_CREDS = {"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"}
SISWA_CREDS = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}

# Test data
TEST_MEMBERS = [
    {"name": "Uji Satu", "student_id": "90001", "class_name": "X IPA 1"},
    {"name": "Uji Dua", "student_id": "90002", "class_name": "X IPA 1"},
    {"name": "Uji Tiga", "student_id": "90003", "class_name": "X IPS 1"}
]

# Sample base64 image (1x1 transparent PNG)
SAMPLE_PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

class TestSession:
    def __init__(self, name, credentials):
        self.name = name
        self.credentials = credentials
        self.session = requests.Session()
        self.user_id = None
        
    def login(self):
        """Login and store session cookie"""
        resp = self.session.post(f"{BASE_URL}/auth/login", json=self.credentials)
        if resp.status_code != 200:
            print(f"❌ {self.name} login failed: {resp.status_code} {resp.text}")
            return False
        print(f"✅ {self.name} logged in successfully")
        return True
    
    def get(self, path):
        """GET request with session"""
        return self.session.get(f"{BASE_URL}{path}")
    
    def post(self, path, json_data=None):
        """POST request with session"""
        return self.session.post(f"{BASE_URL}{path}", json=json_data)
    
    def delete(self, path):
        """DELETE request with session"""
        return self.session.delete(f"{BASE_URL}{path}")

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def test_member_options(admin_session, siswa_session, created_member_ids):
    """Test GET /api/members/options"""
    print_section("TEST 1: GET /api/members/options")
    
    passed = 0
    total = 0
    
    # Test 1.1: Siswa can access member options
    total += 1
    print("\n[1.1] GET /api/members/options as SISWA")
    resp = siswa_session.get("/members/options")
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list):
            # Check if our test members are in the list
            found_members = [m for m in data if m.get("id") in created_member_ids]
            if len(found_members) == len(created_member_ids):
                # Verify fields
                required_fields = ["id", "name", "class_name", "student_id", "photo"]
                all_fields_present = all(
                    all(field in member for field in required_fields)
                    for member in found_members
                )
                if all_fields_present:
                    print(f"✅ PASS: Siswa can access member options, found {len(found_members)} test members with all required fields")
                    passed += 1
                else:
                    print(f"❌ FAIL: Some required fields missing from member objects")
            else:
                print(f"❌ FAIL: Expected {len(created_member_ids)} test members, found {len(found_members)}")
        else:
            print(f"❌ FAIL: Expected list response, got {type(data)}")
    else:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
    
    # Test 1.2: Admin can also access member options
    total += 1
    print("\n[1.2] GET /api/members/options as ADMIN")
    resp = admin_session.get("/members/options")
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list):
            print(f"✅ PASS: Admin can access member options, returned {len(data)} members")
            passed += 1
        else:
            print(f"❌ FAIL: Expected list response")
    else:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
    
    print(f"\n📊 Member Options Test: {passed}/{total} passed")
    return passed, total

def test_member_photo(admin_session, siswa_session, created_member_ids):
    """Test POST /api/members/{member_id}/photo"""
    print_section("TEST 2: POST /api/members/{member_id}/photo")
    
    passed = 0
    total = 0
    
    # Get the first test member ID
    member_id = created_member_ids[0] if created_member_ids else None
    if not member_id:
        print("❌ No test members available for photo test")
        return 0, 0
    
    # Test 2.1: Siswa can update member photo
    total += 1
    print(f"\n[2.1] POST /api/members/{member_id}/photo as SISWA")
    resp = siswa_session.post(f"/members/{member_id}/photo", {"photo": SAMPLE_PHOTO})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("photo") == SAMPLE_PHOTO:
            print(f"✅ PASS: Siswa can update member photo, photo field matches")
            passed += 1
        else:
            print(f"❌ FAIL: Photo field doesn't match expected value")
    else:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
    
    # Test 2.2: Verify photo persisted via GET /api/members/options
    total += 1
    print(f"\n[2.2] Verify photo persisted via GET /api/members/options")
    resp = siswa_session.get("/members/options")
    if resp.status_code == 200:
        data = resp.json()
        member = next((m for m in data if m.get("id") == member_id), None)
        if member and member.get("photo") == SAMPLE_PHOTO:
            print(f"✅ PASS: Photo persisted correctly for member {member_id}")
            passed += 1
        else:
            print(f"❌ FAIL: Photo not found or doesn't match")
    else:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}")
    
    # Test 2.3: Non-existent member ID returns 404
    total += 1
    print(f"\n[2.3] POST /api/members/NONEXISTENT/photo as SISWA")
    resp = siswa_session.post("/members/NONEXISTENT/photo", {"photo": SAMPLE_PHOTO})
    if resp.status_code == 404:
        print(f"✅ PASS: Non-existent member returns 404")
        passed += 1
    else:
        print(f"❌ FAIL: Expected 404, got {resp.status_code}: {resp.text}")
    
    # Test 2.4: Admin can also update member photo
    total += 1
    print(f"\n[2.4] POST /api/members/{member_id}/photo as ADMIN")
    new_photo = "data:image/png;base64,ADMIN_PHOTO_DATA"
    resp = admin_session.post(f"/members/{member_id}/photo", {"photo": new_photo})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("photo") == new_photo:
            print(f"✅ PASS: Admin can update member photo")
            passed += 1
        else:
            print(f"❌ FAIL: Photo field doesn't match")
    else:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
    
    print(f"\n📊 Member Photo Test: {passed}/{total} passed")
    return passed, total

def test_promote_members(admin_session, siswa_session, created_member_ids):
    """Test POST /api/members/promote"""
    print_section("TEST 3: POST /api/members/promote")
    
    passed = 0
    total = 0
    
    # Test 3.1: Admin can promote members from X IPA 1 to XI IPA 1
    total += 1
    print(f"\n[3.1] POST /api/members/promote as ADMIN (X IPA 1 -> XI IPA 1)")
    resp = admin_session.post("/members/promote", {"from_class": "X IPA 1", "to_class": "XI IPA 1"})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok") and data.get("moved") == 2 and data.get("from_class") == "X IPA 1" and data.get("to_class") == "XI IPA 1":
            print(f"✅ PASS: Promotion successful, moved {data.get('moved')} members")
            passed += 1
        else:
            print(f"❌ FAIL: Response structure incorrect: {data}")
    else:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
    
    # Test 3.2: Verify members now have class_name "XI IPA 1"
    total += 1
    print(f"\n[3.2] Verify members promoted to XI IPA 1")
    resp = admin_session.get("/members")
    if resp.status_code == 200:
        data = resp.json()
        promoted_members = [m for m in data if m.get("id") in created_member_ids[:2]]  # First 2 members
        if all(m.get("class_name") == "XI IPA 1" for m in promoted_members):
            print(f"✅ PASS: All promoted members now in XI IPA 1")
            passed += 1
        else:
            print(f"❌ FAIL: Some members not promoted correctly")
    else:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}")
    
    # Test 3.3: Siswa cannot promote members (403)
    total += 1
    print(f"\n[3.3] POST /api/members/promote as SISWA")
    resp = siswa_session.post("/members/promote", {"from_class": "XI IPA 1", "to_class": "XII IPA 1"})
    if resp.status_code == 403:
        print(f"✅ PASS: Siswa correctly denied (403)")
        passed += 1
    else:
        print(f"❌ FAIL: Expected 403, got {resp.status_code}: {resp.text}")
    
    # Test 3.4: Same from_class and to_class returns 400
    total += 1
    print(f"\n[3.4] POST /api/members/promote with same from/to class")
    resp = admin_session.post("/members/promote", {"from_class": "XI IPA 1", "to_class": "XI IPA 1"})
    if resp.status_code == 400:
        print(f"✅ PASS: Same class correctly rejected (400)")
        passed += 1
    else:
        print(f"❌ FAIL: Expected 400, got {resp.status_code}: {resp.text}")
    
    # Test 3.5: Non-existent from_class returns 404
    total += 1
    print(f"\n[3.5] POST /api/members/promote with non-existent from_class")
    resp = admin_session.post("/members/promote", {"from_class": "ZZZ NONEXISTENT", "to_class": "XII IPA 1"})
    if resp.status_code == 404:
        print(f"✅ PASS: Non-existent class correctly returns 404")
        passed += 1
    else:
        print(f"❌ FAIL: Expected 404, got {resp.status_code}: {resp.text}")
    
    print(f"\n📊 Promote Members Test: {passed}/{total} passed")
    return passed, total

def cleanup_test_members(admin_session):
    """Delete all test members to return to empty state"""
    print_section("CLEANUP: Delete all test members")
    
    # Delete members from XI IPA 1 (promoted from X IPA 1)
    print("\n[CLEANUP] Bulk delete XI IPA 1")
    resp = admin_session.post("/members/bulk-delete", {"class_name": "XI IPA 1"})
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Deleted {data.get('deleted', 0)} members from XI IPA 1")
    else:
        print(f"⚠️  Bulk delete XI IPA 1 failed: {resp.status_code}")
    
    # Delete members from X IPS 1
    print("\n[CLEANUP] Bulk delete X IPS 1")
    resp = admin_session.post("/members/bulk-delete", {"class_name": "X IPS 1"})
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Deleted {data.get('deleted', 0)} members from X IPS 1")
    else:
        print(f"⚠️  Bulk delete X IPS 1 failed: {resp.status_code}")
    
    # Verify final count is 0
    print("\n[CLEANUP] Verify final members count = 0")
    resp = admin_session.get("/members")
    if resp.status_code == 200:
        data = resp.json()
        count = len(data)
        if count == 0:
            print(f"✅ Final members count = 0 (data empty as required)")
            return True
        else:
            print(f"⚠️  Final members count = {count} (expected 0)")
            return False
    else:
        print(f"⚠️  Could not verify final count: {resp.status_code}")
        return False

def main():
    print("="*70)
    print("  PERPUSTAKAAN BACKEND TEST - ROUND 6")
    print("  Testing: members/options, members/{id}/photo, members/promote")
    print("="*70)
    
    # Initialize sessions
    admin = TestSession("ADMIN", ADMIN_CREDS)
    siswa = TestSession("SISWA", SISWA_CREDS)
    
    # Login
    print_section("LOGIN")
    if not admin.login():
        print("❌ Admin login failed, cannot continue")
        sys.exit(1)
    if not siswa.login():
        print("❌ Siswa login failed, cannot continue")
        sys.exit(1)
    
    # Create test members
    print_section("SETUP: Create test members")
    created_member_ids = []
    for member_data in TEST_MEMBERS:
        resp = admin.post("/members", member_data)
        if resp.status_code == 200:
            member = resp.json()
            member_id = member.get("id")
            created_member_ids.append(member_id)
            print(f"✅ Created member: {member_data['name']} (ID: {member_id}, Class: {member_data['class_name']})")
        else:
            print(f"❌ Failed to create member {member_data['name']}: {resp.status_code} {resp.text}")
    
    if len(created_member_ids) != len(TEST_MEMBERS):
        print(f"❌ Failed to create all test members, cannot continue")
        sys.exit(1)
    
    # Run tests
    total_passed = 0
    total_tests = 0
    
    p, t = test_member_options(admin, siswa, created_member_ids)
    total_passed += p
    total_tests += t
    
    p, t = test_member_photo(admin, siswa, created_member_ids)
    total_passed += p
    total_tests += t
    
    p, t = test_promote_members(admin, siswa, created_member_ids)
    total_passed += p
    total_tests += t
    
    # Cleanup
    cleanup_success = cleanup_test_members(admin)
    
    # Final summary
    print_section("FINAL SUMMARY")
    print(f"\n📊 Total Tests: {total_passed}/{total_tests} passed")
    print(f"🧹 Cleanup: {'✅ Success' if cleanup_success else '⚠️  Incomplete'}")
    
    if total_passed == total_tests and cleanup_success:
        print("\n✅ ALL TESTS PASSED - Round 6 Complete")
        sys.exit(0)
    else:
        print(f"\n❌ SOME TESTS FAILED - {total_tests - total_passed} failures")
        sys.exit(1)

if __name__ == "__main__":
    main()
