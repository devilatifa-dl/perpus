#!/usr/bin/env python3
"""
Backend API Test Suite for Perpustakaan - Round 4 Settings Changes
Tests PUT/GET /api/settings with new fields:
- card_school_name
- card_font_size
- card_school_logo_pos
- card_library_logo_pos
"""

import requests
import json

# Configuration
BASE_URL = "https://perpus-app-6.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_CREDS = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
SISWA_CREDS = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}

def login(credentials):
    """Login and return session with cookies"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/auth/login", json=credentials)
    if resp.status_code != 200:
        raise Exception(f"Login failed: {resp.status_code} {resp.text}")
    return session

def test_admin_put_settings_with_new_fields():
    """Test 1: Admin PUT /api/settings with new round-4 fields"""
    print("\n" + "="*80)
    print("TEST 1: Admin PUT /api/settings with new fields")
    print("="*80)
    
    session = login(ADMIN_CREDS)
    
    # Settings payload with NEW fields
    settings_payload = {
        "school_logo": "",
        "library_logo": "",
        "card_theme": "book",
        "card_layout": "classic",
        "card_show_qr": True,
        "card_show_address": True,
        "card_title": "KARTU ANGGOTA PERPUSTAKAAN",
        "card_school_name": "SMA NEGERI 1 ABUNG TENGAH",
        "card_font": "elegan",
        "card_font_size": "besar",
        "card_school_logo_pos": "kiri",
        "card_library_logo_pos": "kanan",
        "card_photo_pos": "kiri",
        "card_qr_pos": "atas"
    }
    
    resp = session.put(f"{BASE_URL}/settings", json=settings_payload)
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Response: {resp.text}")
        print("❌ FAILED: Expected 200, got", resp.status_code)
        return False
    
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    print("✅ PASSED: Admin can PUT settings with new fields (200)")
    return True

def test_get_settings_reflects_new_values():
    """Test 2: GET /api/settings reflects the new field values"""
    print("\n" + "="*80)
    print("TEST 2: GET /api/settings reflects new field values")
    print("="*80)
    
    session = login(ADMIN_CREDS)
    
    resp = session.get(f"{BASE_URL}/settings")
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Response: {resp.text}")
        print("❌ FAILED: Expected 200, got", resp.status_code)
        return False
    
    data = resp.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    # Verify new field values
    expected_values = {
        "card_school_name": "SMA NEGERI 1 ABUNG TENGAH",
        "card_font_size": "besar",
        "card_school_logo_pos": "kiri",
        "card_library_logo_pos": "kanan",
        "card_theme": "book"
    }
    
    all_match = True
    for key, expected_val in expected_values.items():
        actual_val = data.get(key)
        if actual_val != expected_val:
            print(f"❌ FAILED: {key} expected '{expected_val}', got '{actual_val}'")
            all_match = False
        else:
            print(f"✅ {key}: {actual_val}")
    
    if not all_match:
        return False
    
    print("✅ PASSED: All new field values correctly saved and retrieved")
    return True

def test_siswa_cannot_put_settings():
    """Test 3: Siswa cannot PUT /api/settings (403)"""
    print("\n" + "="*80)
    print("TEST 3: Siswa cannot PUT /api/settings")
    print("="*80)
    
    session = login(SISWA_CREDS)
    
    settings_payload = {
        "card_theme": "navy",
        "card_school_name": "HACKED"
    }
    
    resp = session.put(f"{BASE_URL}/settings", json=settings_payload)
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 403:
        print(f"Response: {resp.text}")
        print("❌ FAILED: Expected 403, got", resp.status_code)
        return False
    
    print(f"Response: {resp.json()}")
    print("✅ PASSED: Siswa correctly blocked from PUT settings (403)")
    return True

def test_siswa_can_get_settings():
    """Test 4: Siswa CAN GET /api/settings (200)"""
    print("\n" + "="*80)
    print("TEST 4: Siswa CAN GET /api/settings")
    print("="*80)
    
    session = login(SISWA_CREDS)
    
    resp = session.get(f"{BASE_URL}/settings")
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Response: {resp.text}")
        print("❌ FAILED: Expected 200, got", resp.status_code)
        return False
    
    data = resp.json()
    print(f"Response keys: {list(data.keys())}")
    print("✅ PASSED: Siswa can GET settings (200)")
    return True

def test_data_still_empty():
    """Test 5: Confirm data still empty (GET /api/members length 0)"""
    print("\n" + "="*80)
    print("TEST 5: Confirm data still empty")
    print("="*80)
    
    session = login(ADMIN_CREDS)
    
    resp = session.get(f"{BASE_URL}/members")
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Response: {resp.text}")
        print("❌ FAILED: Expected 200, got", resp.status_code)
        return False
    
    members = resp.json()
    member_count = len(members)
    
    print(f"Members count: {member_count}")
    if member_count != 0:
        print(f"❌ FAILED: Expected 0 members, got {member_count}")
        return False
    
    print("✅ PASSED: Data still empty (members count = 0)")
    return True

def test_cleanup_restore_defaults():
    """Test 6: CLEANUP - Restore settings to defaults"""
    print("\n" + "="*80)
    print("TEST 6: CLEANUP - Restore settings to defaults")
    print("="*80)
    
    session = login(ADMIN_CREDS)
    
    # Default settings payload
    default_settings = {
        "school_logo": "",
        "library_logo": "",
        "card_theme": "navy",
        "card_layout": "classic",
        "card_show_qr": True,
        "card_show_address": True,
        "card_title": "KARTU ANGGOTA PERPUSTAKAAN",
        "card_school_name": "SMA 1 NEGERI ABUNG TENGAH",
        "card_font": "modern",
        "card_font_size": "sedang",
        "card_school_logo_pos": "kiri",
        "card_library_logo_pos": "kanan",
        "card_photo_pos": "kiri",
        "card_qr_pos": "atas"
    }
    
    resp = session.put(f"{BASE_URL}/settings", json=default_settings)
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Response: {resp.text}")
        print("❌ FAILED: Expected 200, got", resp.status_code)
        return False
    
    # Verify defaults were restored
    resp = session.get(f"{BASE_URL}/settings")
    data = resp.json()
    
    if data.get("card_theme") != "navy" or data.get("card_font_size") != "sedang":
        print(f"❌ FAILED: Defaults not restored correctly")
        print(f"   card_theme: {data.get('card_theme')} (expected 'navy')")
        print(f"   card_font_size: {data.get('card_font_size')} (expected 'sedang')")
        return False
    
    print(f"Response: {json.dumps(data, indent=2)}")
    print("✅ PASSED: Settings restored to defaults")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PERPUSTAKAAN BACKEND TEST SUITE - ROUND 4 SETTINGS")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_CREDS['email']}")
    print(f"Siswa: {SISWA_CREDS['email']}")
    
    tests = [
        ("Admin PUT settings with new fields", test_admin_put_settings_with_new_fields),
        ("GET settings reflects new values", test_get_settings_reflects_new_values),
        ("Siswa cannot PUT settings (403)", test_siswa_cannot_put_settings),
        ("Siswa CAN GET settings (200)", test_siswa_can_get_settings),
        ("Data still empty (members=0)", test_data_still_empty),
        ("CLEANUP - Restore defaults", test_cleanup_restore_defaults),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
