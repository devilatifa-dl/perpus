#!/usr/bin/env python3
"""
Backend API Test Suite for Perpustakaan - Round 5
Tests:
1. GET /api/overdue - overdue window changed from 7 to 3 days
2. GET /api/account/member - siswa own member
3. POST /api/account/photo - siswa photo upload
4. GET /api/admin/backup - backup data
5. POST /api/admin/restore - restore data
"""

import requests
import json
import io

# Configuration
BASE_URL = "https://perpus-app-6.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_CREDS = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
PETUGAS_CREDS = {"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"}
SISWA_CREDS = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}

def login(credentials):
    """Login and return session with cookies"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/auth/login", json=credentials)
    if resp.status_code != 200:
        raise Exception(f"Login failed: {resp.status_code} {resp.text}")
    return session

def test_overdue_window():
    """Test 1: GET /api/overdue returns days=3 (staff only)"""
    print("\n" + "="*80)
    print("TEST 1: Overdue Window Changed (7 -> 3 days)")
    print("="*80)
    
    # Test as admin (staff)
    print("\n1.1: Admin accessing /api/overdue")
    session = login(ADMIN_CREDS)
    resp = session.get(f"{BASE_URL}/overdue")
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    data = resp.json()
    
    if 'days' not in data:
        print("❌ FAILED: Response missing 'days' field")
        return False
    
    if data['days'] != 3:
        print(f"❌ FAILED: Expected days=3, got days={data['days']}")
        return False
    
    print(f"✅ Admin: days={data['days']} (correct)")
    
    # Test as petugas (staff)
    print("\n1.2: Petugas accessing /api/overdue")
    session = login(PETUGAS_CREDS)
    resp = session.get(f"{BASE_URL}/overdue")
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    data = resp.json()
    if data['days'] != 3:
        print(f"❌ FAILED: Expected days=3, got days={data['days']}")
        return False
    
    print(f"✅ Petugas: days={data['days']} (correct)")
    
    # Test as siswa (should get 403)
    print("\n1.3: Siswa accessing /api/overdue (should get 403)")
    session = login(SISWA_CREDS)
    resp = session.get(f"{BASE_URL}/overdue")
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    print("✅ Siswa: 403 (correct)")
    
    print("\n✅ PASSED: Overdue window correctly returns days=3, staff only")
    return True

def test_siswa_member_and_photo():
    """Test 2 & 3: GET /api/account/member and POST /api/account/photo"""
    print("\n" + "="*80)
    print("TEST 2 & 3: Siswa Own Member + Photo")
    print("="*80)
    
    # Test 2.1: GET /api/account/member as siswa (may be null initially)
    print("\n2.1: GET /api/account/member as siswa")
    session_siswa = login(SISWA_CREDS)
    resp = session_siswa.get(f"{BASE_URL}/account/member")
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    initial_member = resp.json()
    print(f"✅ Siswa GET member: {initial_member}")
    
    # Test 2.2: GET /api/account/member as admin (should return null)
    print("\n2.2: GET /api/account/member as admin (should return null)")
    session_admin = login(ADMIN_CREDS)
    resp = session_admin.get(f"{BASE_URL}/account/member")
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    if resp.json() is not None:
        print(f"❌ FAILED: Expected null for admin, got {resp.json()}")
        return False
    
    print("✅ Admin GET member: null (correct)")
    
    # Test 2.3: GET /api/account/member as petugas (should return null)
    print("\n2.3: GET /api/account/member as petugas (should return null)")
    session_petugas = login(PETUGAS_CREDS)
    resp = session_petugas.get(f"{BASE_URL}/account/member")
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    if resp.json() is not None:
        print(f"❌ FAILED: Expected null for petugas, got {resp.json()}")
        return False
    
    print("✅ Petugas GET member: null (correct)")
    
    # Test 3.1: POST /api/account/photo as siswa
    print("\n3.1: POST /api/account/photo as siswa")
    photo_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    resp = session_siswa.post(f"{BASE_URL}/account/photo", json={"photo": photo_data})
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    member_with_photo = resp.json()
    
    if 'photo' not in member_with_photo:
        print("❌ FAILED: Response missing 'photo' field")
        return False
    
    if member_with_photo['photo'] != photo_data:
        print("❌ FAILED: Photo data mismatch")
        return False
    
    print(f"✅ Siswa POST photo: member returned with photo set")
    
    # Store member_id for cleanup
    member_id = member_with_photo.get('id')
    
    # Test 3.2: GET /api/account/member again to verify photo persisted
    print("\n3.2: GET /api/account/member again (verify photo persisted)")
    resp = session_siswa.get(f"{BASE_URL}/account/member")
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    member_check = resp.json()
    
    if member_check is None:
        print("❌ FAILED: Member should exist after photo upload")
        return False
    
    if member_check.get('photo') != photo_data:
        print("❌ FAILED: Photo not persisted correctly")
        return False
    
    print("✅ Photo persisted correctly")
    
    # Test 3.3: POST /api/account/photo as admin (should get 403)
    print("\n3.3: POST /api/account/photo as admin (should get 403)")
    resp = session_admin.post(f"{BASE_URL}/account/photo", json={"photo": photo_data})
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    print("✅ Admin POST photo: 403 (correct)")
    
    # Test 3.4: POST /api/account/photo as petugas (should get 403)
    print("\n3.4: POST /api/account/photo as petugas (should get 403)")
    resp = session_petugas.post(f"{BASE_URL}/account/photo", json={"photo": photo_data})
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    print("✅ Petugas POST photo: 403 (correct)")
    
    # CLEANUP: Delete the auto-created member
    print("\n3.5: CLEANUP - Delete auto-created siswa member")
    if member_id:
        resp = session_admin.delete(f"{BASE_URL}/members/{member_id}")
        print(f"Delete Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            print(f"✅ Deleted member {member_id}")
        else:
            print(f"⚠️  Could not delete member {member_id}: {resp.status_code}")
    
    # Verify members count is 0
    print("\n3.6: Verify members count = 0")
    resp = session_admin.get(f"{BASE_URL}/members")
    members = resp.json()
    print(f"Final members count: {len(members)}")
    
    if len(members) != 0:
        print(f"⚠️  WARNING: Expected 0 members, got {len(members)}")
        print("Remaining members:")
        for m in members:
            print(f"  - {m.get('name')} ({m.get('student_id')}) - {m.get('class_name')}")
    else:
        print("✅ Members count = 0 (correct)")
    
    print("\n✅ PASSED: Siswa member + photo endpoints working correctly")
    return True

def test_backup():
    """Test 4: GET /api/admin/backup"""
    print("\n" + "="*80)
    print("TEST 4: Backup Data")
    print("="*80)
    
    # Test 4.1: GET /api/admin/backup as admin
    print("\n4.1: GET /api/admin/backup as admin")
    session_admin = login(ADMIN_CREDS)
    resp = session_admin.get(f"{BASE_URL}/admin/backup")
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    backup_data = resp.json()
    print(f"Response keys: {list(backup_data.keys())}")
    
    # Verify required keys
    required_keys = ['app', 'version', 'generated_at', 'collections']
    for key in required_keys:
        if key not in backup_data:
            print(f"❌ FAILED: Missing required key '{key}'")
            return False
    
    print(f"✅ Admin backup: has all required keys {required_keys}")
    
    # Verify collections object
    collections = backup_data['collections']
    required_collections = ['books', 'members', 'transactions', 'incoming', 'missing', 'reservations', 'stocktake', 'shelves', 'settings']
    
    print(f"Collections keys: {list(collections.keys())}")
    
    for coll in required_collections:
        if coll not in collections:
            print(f"❌ FAILED: Missing collection '{coll}'")
            return False
    
    print(f"✅ Collections object has all required collections: {required_collections}")
    
    # Store backup for restore test
    global BACKUP_DATA
    BACKUP_DATA = backup_data
    
    # Test 4.2: GET /api/admin/backup as petugas (should get 403)
    print("\n4.2: GET /api/admin/backup as petugas (should get 403)")
    session_petugas = login(PETUGAS_CREDS)
    resp = session_petugas.get(f"{BASE_URL}/admin/backup")
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    print("✅ Petugas: 403 (correct)")
    
    # Test 4.3: GET /api/admin/backup as siswa (should get 403)
    print("\n4.3: GET /api/admin/backup as siswa (should get 403)")
    session_siswa = login(SISWA_CREDS)
    resp = session_siswa.get(f"{BASE_URL}/admin/backup")
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    print("✅ Siswa: 403 (correct)")
    
    print("\n✅ PASSED: Backup endpoint working correctly")
    return True

def test_restore():
    """Test 5: POST /api/admin/restore"""
    print("\n" + "="*80)
    print("TEST 5: Restore Data")
    print("="*80)
    
    # Test 5.1: Safe round-trip restore as admin
    print("\n5.1: POST /api/admin/restore as admin (safe round-trip)")
    session_admin = login(ADMIN_CREDS)
    
    # Use backup from previous test
    if 'BACKUP_DATA' not in globals():
        print("❌ FAILED: No backup data available (run backup test first)")
        return False
    
    backup_json = json.dumps(BACKUP_DATA)
    
    # Create file-like object
    files = {
        'file': ('backup.json', backup_json, 'application/json')
    }
    
    resp = session_admin.post(f"{BASE_URL}/admin/restore", files=files)
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {resp.status_code}")
        return False
    
    restore_result = resp.json()
    
    if 'ok' not in restore_result or restore_result['ok'] != True:
        print("❌ FAILED: Response missing 'ok: true'")
        return False
    
    if 'restored' not in restore_result:
        print("❌ FAILED: Response missing 'restored' object")
        return False
    
    print(f"✅ Admin restore: {restore_result}")
    
    # Test 5.2: POST /api/admin/restore as petugas (should get 403)
    print("\n5.2: POST /api/admin/restore as petugas (should get 403)")
    session_petugas = login(PETUGAS_CREDS)
    
    files = {
        'file': ('backup.json', backup_json, 'application/json')
    }
    
    resp = session_petugas.post(f"{BASE_URL}/admin/restore", files=files)
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    print("✅ Petugas: 403 (correct)")
    
    # Test 5.3: POST /api/admin/restore as siswa (should get 403)
    print("\n5.3: POST /api/admin/restore as siswa (should get 403)")
    session_siswa = login(SISWA_CREDS)
    
    files = {
        'file': ('backup.json', backup_json, 'application/json')
    }
    
    resp = session_siswa.post(f"{BASE_URL}/admin/restore", files=files)
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    print("✅ Siswa: 403 (correct)")
    
    # Test 5.4: Invalid JSON file (should get 400)
    print("\n5.4: POST /api/admin/restore with invalid JSON (should get 400)")
    
    invalid_json = "not json at all"
    files = {
        'file': ('backup.json', invalid_json, 'application/json')
    }
    
    resp = session_admin.post(f"{BASE_URL}/admin/restore", files=files)
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 400:
        print(f"❌ FAILED: Expected 400, got {resp.status_code}")
        return False
    
    print("✅ Invalid JSON: 400 (correct)")
    
    # Test 5.5: Valid JSON but missing 'collections' (should get 400)
    print("\n5.5: POST /api/admin/restore with JSON missing 'collections' (should get 400)")
    
    invalid_structure = json.dumps({"foo": 1})
    files = {
        'file': ('backup.json', invalid_structure, 'application/json')
    }
    
    resp = session_admin.post(f"{BASE_URL}/admin/restore", files=files)
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 400:
        print(f"❌ FAILED: Expected 400, got {resp.status_code}")
        return False
    
    print("✅ Missing 'collections': 400 (correct)")
    
    # Test 5.6: Verify data remains empty
    print("\n5.6: Verify library data remains empty")
    resp = session_admin.get(f"{BASE_URL}/members")
    members = resp.json()
    print(f"Members count: {len(members)}")
    
    if len(members) != 0:
        print(f"⚠️  WARNING: Expected 0 members, got {len(members)}")
    else:
        print("✅ Members count = 0 (correct)")
    
    print("\n✅ PASSED: Restore endpoint working correctly")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PERPUSTAKAAN BACKEND TEST SUITE - ROUND 5")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    
    results = []
    
    try:
        # Run tests in order
        results.append(("Overdue Window (7->3 days)", test_overdue_window()))
        results.append(("Siswa Member + Photo", test_siswa_member_and_photo()))
        results.append(("Backup Data", test_backup()))
        results.append(("Restore Data", test_restore()))
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Critical Error", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
