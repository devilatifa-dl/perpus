#!/usr/bin/env python3
"""
Backend API Test Suite for Perpustakaan - Bulk Member Import
Tests POST /api/members/import endpoint
"""

import requests
import io
import csv
from openpyxl import Workbook

# Configuration
BASE_URL = "https://perpus-library.preview.emergentagent.com/api"

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

def test_csv_happy_path_with_skips():
    """Test 1: CSV upload with valid rows, duplicate NIS, and empty kelas"""
    print("\n" + "="*80)
    print("TEST 1: CSV Happy Path with Skips")
    print("="*80)
    
    session = login(ADMIN_CREDS)
    
    # Create CSV content exactly as specified
    csv_content = """nama,nis,kelas
Budi Santoso,30001,X TEST A
Siti Aminah,30002,X TEST A
Budi Duplicate,30001,X TEST A
Tanpa Kelas,30003,"""
    
    # Upload CSV
    files = {'file': ('anggota.csv', csv_content, 'text/csv')}
    resp = session.post(f"{BASE_URL}/members/import", files=files)
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code != 200:
        print("❌ FAILED: Expected 200, got", resp.status_code)
        return False
    
    data = resp.json()
    
    # Verify response structure
    if not all(k in data for k in ['imported', 'skipped', 'total', 'errors']):
        print("❌ FAILED: Missing required keys in response")
        return False
    
    # Verify counts
    if data['imported'] != 2:
        print(f"❌ FAILED: Expected imported=2, got {data['imported']}")
        return False
    
    if data['skipped'] != 2:
        print(f"❌ FAILED: Expected skipped=2, got {data['skipped']}")
        return False
    
    if data['total'] != 4:
        print(f"❌ FAILED: Expected total=4, got {data['total']}")
        return False
    
    if len(data['errors']) != 2:
        print(f"❌ FAILED: Expected 2 errors, got {len(data['errors'])}")
        return False
    
    # Verify members were created
    resp = session.get(f"{BASE_URL}/members")
    members = resp.json()
    
    test_members = [m for m in members if m['class_name'] == 'X TEST A']
    if len(test_members) != 2:
        print(f"❌ FAILED: Expected 2 members in X TEST A, got {len(test_members)}")
        return False
    
    # Verify names
    names = {m['name'] for m in test_members}
    expected_names = {'Budi Santoso', 'Siti Aminah'}
    if names != expected_names:
        print(f"❌ FAILED: Expected names {expected_names}, got {names}")
        return False
    
    print("✅ PASSED: CSV import with skips working correctly")
    print(f"   - Imported: {data['imported']} (Budi Santoso, Siti Aminah)")
    print(f"   - Skipped: {data['skipped']} (duplicate NIS 30001, empty kelas)")
    print(f"   - Errors: {data['errors']}")
    return True

def test_xlsx_format():
    """Test 2: XLSX upload"""
    print("\n" + "="*80)
    print("TEST 2: XLSX Format")
    print("="*80)
    
    session = login(ADMIN_CREDS)
    
    # Create XLSX in memory
    wb = Workbook()
    ws = wb.active
    ws.append(['nama', 'nis', 'kelas'])
    ws.append(['Rina', '30010', 'XI TEST B'])
    ws.append(['Tono', '30011', 'XI TEST B'])
    
    # Save to BytesIO
    xlsx_buffer = io.BytesIO()
    wb.save(xlsx_buffer)
    xlsx_buffer.seek(0)
    
    # Upload XLSX
    files = {'file': ('anggota.xlsx', xlsx_buffer.read(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    resp = session.post(f"{BASE_URL}/members/import", files=files)
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code != 200:
        print("❌ FAILED: Expected 200, got", resp.status_code)
        return False
    
    data = resp.json()
    
    if data['imported'] != 2:
        print(f"❌ FAILED: Expected imported=2, got {data['imported']}")
        return False
    
    # Verify members were created
    resp = session.get(f"{BASE_URL}/members")
    members = resp.json()
    
    test_members = [m for m in members if m['class_name'] == 'XI TEST B']
    if len(test_members) != 2:
        print(f"❌ FAILED: Expected 2 members in XI TEST B, got {len(test_members)}")
        return False
    
    print("✅ PASSED: XLSX import working correctly")
    print(f"   - Imported: {data['imported']} (Rina, Tono)")
    return True

def test_unsupported_extension():
    """Test 3: Unsupported file extension (.txt)"""
    print("\n" + "="*80)
    print("TEST 3: Unsupported Extension")
    print("="*80)
    
    session = login(ADMIN_CREDS)
    
    # Upload .txt file
    txt_content = "nama,nis,kelas\nTest,12345,X A"
    files = {'file': ('anggota.txt', txt_content, 'text/plain')}
    resp = session.post(f"{BASE_URL}/members/import", files=files)
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
    
    if resp.status_code != 400:
        print(f"❌ FAILED: Expected 400, got {resp.status_code}")
        return False
    
    print("✅ PASSED: Unsupported extension correctly rejected with 400")
    return True

def test_permission_siswa():
    """Test 4: Siswa should get 403"""
    print("\n" + "="*80)
    print("TEST 4: Permission Check (Siswa)")
    print("="*80)
    
    session = login(SISWA_CREDS)
    
    # Try to upload as siswa
    csv_content = "nama,nis,kelas\nTest,99999,XII A"
    files = {'file': ('anggota.csv', csv_content, 'text/csv')}
    resp = session.post(f"{BASE_URL}/members/import", files=files)
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
    
    if resp.status_code != 403:
        print(f"❌ FAILED: Expected 403, got {resp.status_code}")
        return False
    
    print("✅ PASSED: Siswa correctly denied with 403")
    return True

def cleanup_test_data():
    """Test 5: CLEANUP - Delete all test members"""
    print("\n" + "="*80)
    print("TEST 5: CLEANUP - Delete All Test Members")
    print("="*80)
    
    session = login(ADMIN_CREDS)
    
    # Delete X TEST A class
    print("\nDeleting class: X TEST A")
    resp = session.post(f"{BASE_URL}/members/bulk-delete", json={"class_name": "X TEST A"})
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {data}")
        print(f"✅ Deleted {data.get('deleted', 0)} members from X TEST A")
    elif resp.status_code == 404:
        print("⚠️  No members found in X TEST A (already cleaned or never created)")
    else:
        print(f"❌ FAILED: Unexpected status {resp.status_code}: {resp.text}")
        return False
    
    # Delete XI TEST B class
    print("\nDeleting class: XI TEST B")
    resp = session.post(f"{BASE_URL}/members/bulk-delete", json={"class_name": "XI TEST B"})
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {data}")
        print(f"✅ Deleted {data.get('deleted', 0)} members from XI TEST B")
    elif resp.status_code == 404:
        print("⚠️  No members found in XI TEST B (already cleaned or never created)")
    else:
        print(f"❌ FAILED: Unexpected status {resp.status_code}: {resp.text}")
        return False
    
    # Verify members list is empty
    print("\nVerifying members list is empty...")
    resp = session.get(f"{BASE_URL}/members")
    members = resp.json()
    
    print(f"Final members count: {len(members)}")
    
    if len(members) != 0:
        print(f"❌ FAILED: Expected 0 members, got {len(members)}")
        print("Remaining members:")
        for m in members:
            print(f"  - {m['name']} ({m['student_id']}) - {m['class_name']}")
        return False
    
    print("✅ PASSED: All test members cleaned up, members count = 0")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("BULK MEMBER IMPORT TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    
    results = []
    
    try:
        # Run tests in order
        results.append(("CSV Happy Path with Skips", test_csv_happy_path_with_skips()))
        results.append(("XLSX Format", test_xlsx_format()))
        results.append(("Unsupported Extension", test_unsupported_extension()))
        results.append(("Permission Check (Siswa)", test_permission_siswa()))
        results.append(("Cleanup Test Data", cleanup_test_data()))
        
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
