#!/usr/bin/env python3
"""
Backend Test Suite - Round 7: Reservation with Member Selection
Tests the shared siswa kiosk feature where reservations record the actual ordering member's name.
"""

import requests
import json
import sys
from typing import Dict, Optional

# Base URL from frontend/.env
BASE_URL = "https://perpus-app-6.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
SISWA_CREDS = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}

class TestSession:
    def __init__(self):
        self.admin_session = requests.Session()
        self.siswa_session = requests.Session()
        self.test_data = {
            "members": [],
            "books": [],
            "reservations": []
        }
    
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
    
    def setup_test_data(self) -> bool:
        """Create test members and books as admin"""
        print("\n=== SETUP: Creating Test Data ===")
        
        # Create 2 test members
        members_to_create = [
            {"name": "Andi", "student_id": "70001", "class_name": "XII IPA 1"},
            {"name": "Budi", "student_id": "70002", "class_name": "XII IPA 1"}
        ]
        
        for member_data in members_to_create:
            try:
                resp = self.admin_session.post(f"{BASE_URL}/members", json=member_data)
                if resp.status_code == 200:
                    member = resp.json()
                    self.test_data["members"].append(member)
                    print(f"✓ Created member: {member['name']} (ID: {member['id']}, NIS: {member['student_id']})")
                else:
                    print(f"✗ Failed to create member {member_data['name']}: {resp.status_code} {resp.text}")
                    return False
            except Exception as e:
                print(f"✗ Error creating member {member_data['name']}: {e}")
                return False
        
        # Check if books exist
        try:
            resp = self.admin_session.get(f"{BASE_URL}/books")
            if resp.status_code == 200:
                books = resp.json()
                available_books = [b for b in books if b.get("status") == "Tersedia"]
                
                if len(available_books) >= 2:
                    self.test_data["books"] = available_books[:2]
                    print(f"✓ Found {len(available_books)} available books, using 2 for tests")
                    for book in self.test_data["books"]:
                        print(f"  - {book['title']} (ID: {book['id']}, Status: {book['status']})")
                else:
                    # Need to create books
                    print(f"Only {len(available_books)} available books found, creating 2 test books...")
                    books_to_create = [
                        {
                            "title": "Test Book Round 7 Alpha",
                            "author": "Test Author A",
                            "category": "Test",
                            "shelf": "R-01",
                            "isbn": "TEST-70001",
                            "cover": "",
                            "status": "Tersedia"
                        },
                        {
                            "title": "Test Book Round 7 Beta",
                            "author": "Test Author B",
                            "category": "Test",
                            "shelf": "R-01",
                            "isbn": "TEST-70002",
                            "cover": "",
                            "status": "Tersedia"
                        }
                    ]
                    
                    for book_data in books_to_create:
                        resp = self.admin_session.post(f"{BASE_URL}/books", json=book_data)
                        if resp.status_code == 200:
                            book = resp.json()
                            self.test_data["books"].append(book)
                            print(f"✓ Created book: {book['title']} (ID: {book['id']})")
                        else:
                            print(f"✗ Failed to create book: {resp.status_code} {resp.text}")
                            return False
            else:
                print(f"✗ Failed to get books: {resp.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error checking/creating books: {e}")
            return False
        
        print(f"\n✓ Setup complete: {len(self.test_data['members'])} members, {len(self.test_data['books'])} books")
        return True
    
    def cleanup(self) -> bool:
        """Clean up all test data"""
        print("\n=== CLEANUP: Removing Test Data ===")
        success = True
        
        # Cancel/delete all test reservations
        for res in self.test_data["reservations"]:
            try:
                resp = self.admin_session.delete(f"{BASE_URL}/reservations/{res['id']}")
                if resp.status_code in [200, 404]:
                    print(f"✓ Deleted reservation {res['id']}")
                else:
                    print(f"✗ Failed to delete reservation {res['id']}: {resp.status_code}")
                    success = False
            except Exception as e:
                print(f"✗ Error deleting reservation {res['id']}: {e}")
                success = False
        
        # Bulk delete test members by class
        if self.test_data["members"]:
            try:
                resp = self.admin_session.post(f"{BASE_URL}/members/bulk-delete", json={"class_name": "XII IPA 1"})
                if resp.status_code == 200:
                    result = resp.json()
                    print(f"✓ Bulk deleted members from XII IPA 1: {result.get('deleted', 0)} deleted")
                elif resp.status_code == 404:
                    print(f"✓ No members found in XII IPA 1 (already cleaned)")
                else:
                    print(f"✗ Failed to bulk delete members: {resp.status_code} {resp.text}")
                    success = False
            except Exception as e:
                print(f"✗ Error bulk deleting members: {e}")
                success = False
        
        # Delete test books if we created them
        for book in self.test_data["books"]:
            if "Test Book Round 7" in book.get("title", ""):
                try:
                    resp = self.admin_session.delete(f"{BASE_URL}/books/{book['id']}")
                    if resp.status_code in [200, 404]:
                        print(f"✓ Deleted test book {book['id']}")
                    else:
                        print(f"✗ Failed to delete book {book['id']}: {resp.status_code}")
                        success = False
                except Exception as e:
                    print(f"✗ Error deleting book {book['id']}: {e}")
                    success = False
        
        # Verify members count is 0
        try:
            resp = self.admin_session.get(f"{BASE_URL}/members")
            if resp.status_code == 200:
                members = resp.json()
                print(f"\n✓ Final members count: {len(members)}")
                if len(members) != 0:
                    print(f"⚠ WARNING: Expected 0 members, found {len(members)}")
                    success = False
            else:
                print(f"✗ Failed to verify members count: {resp.status_code}")
                success = False
        except Exception as e:
            print(f"✗ Error verifying members count: {e}")
            success = False
        
        return success
    
    def run_tests(self) -> bool:
        """Run all test scenarios"""
        print("\n" + "="*70)
        print("ROUND 7 BACKEND TESTS: Reservation with Member Selection")
        print("="*70)
        
        # Login
        if not self.login(self.admin_session, ADMIN_CREDS):
            return False
        if not self.login(self.siswa_session, SISWA_CREDS):
            return False
        
        # Setup
        if not self.setup_test_data():
            return False
        
        # Get member IDs
        andi_id = self.test_data["members"][0]["id"]
        budi_id = self.test_data["members"][1]["id"]
        book1_id = self.test_data["books"][0]["id"]
        book2_id = self.test_data["books"][1]["id"]
        
        print(f"\nTest IDs:")
        print(f"  ANDI_ID: {andi_id}")
        print(f"  BUDI_ID: {budi_id}")
        print(f"  BOOK1_ID: {book1_id}")
        print(f"  BOOK2_ID: {book2_id}")
        
        all_passed = True
        
        # TEST 1: Siswa creates reservation with member_id for Andi
        print("\n--- TEST 1: Siswa POST /api/reservations with member_id (Andi) ---")
        try:
            resp = self.siswa_session.post(f"{BASE_URL}/reservations", json={
                "book_id": book1_id,
                "member_id": andi_id
            })
            if resp.status_code == 200:
                reservation = resp.json()
                self.test_data["reservations"].append(reservation)
                andi_res_id = reservation["id"]
                
                # Verify member_name and class_name
                if reservation.get("member_name") == "Andi" and reservation.get("class_name") == "XII IPA 1":
                    print(f"✅ PASS: Reservation created with member_name='{reservation['member_name']}', class_name='{reservation['class_name']}'")
                    print(f"   Reservation ID: {andi_res_id}")
                else:
                    print(f"❌ FAIL: Expected member_name='Andi', class_name='XII IPA 1'")
                    print(f"   Got: member_name='{reservation.get('member_name')}', class_name='{reservation.get('class_name')}'")
                    all_passed = False
            else:
                print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
                all_passed = False
                andi_res_id = None
        except Exception as e:
            print(f"❌ FAIL: Exception: {e}")
            all_passed = False
            andi_res_id = None
        
        # TEST 2: Admin GET /api/reservations shows Andi's reservation
        print("\n--- TEST 2: Admin GET /api/reservations (verify Andi's reservation) ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/reservations")
            if resp.status_code == 200:
                reservations = resp.json()
                andi_res = next((r for r in reservations if r.get("id") == andi_res_id), None)
                if andi_res:
                    if andi_res.get("member_name") == "Andi" and andi_res.get("class_name") == "XII IPA 1":
                        print(f"✅ PASS: Admin sees reservation with member_name='Andi', class_name='XII IPA 1'")
                    else:
                        print(f"❌ FAIL: Expected member_name='Andi', class_name='XII IPA 1'")
                        print(f"   Got: member_name='{andi_res.get('member_name')}', class_name='{andi_res.get('class_name')}'")
                        all_passed = False
                else:
                    print(f"❌ FAIL: Reservation {andi_res_id} not found in admin's list")
                    all_passed = False
            else:
                print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
                all_passed = False
        except Exception as e:
            print(f"❌ FAIL: Exception: {e}")
            all_passed = False
        
        # TEST 3: GET /api/reservations/mine with member_id filtering
        print("\n--- TEST 3: Siswa GET /api/reservations/mine?member_id filtering ---")
        try:
            # 3a: Get Andi's reservations
            resp = self.siswa_session.get(f"{BASE_URL}/reservations/mine?member_id={andi_id}")
            if resp.status_code == 200:
                andi_reservations = resp.json()
                if len(andi_reservations) > 0 and any(r.get("id") == andi_res_id for r in andi_reservations):
                    print(f"✅ PASS: GET /api/reservations/mine?member_id={andi_id} returns Andi's reservation")
                else:
                    print(f"❌ FAIL: Andi's reservation not found in member_id={andi_id} query")
                    all_passed = False
            else:
                print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
                all_passed = False
            
            # 3b: Get Budi's reservations (should not contain Andi's)
            resp = self.siswa_session.get(f"{BASE_URL}/reservations/mine?member_id={budi_id}")
            if resp.status_code == 200:
                budi_reservations = resp.json()
                if not any(r.get("id") == andi_res_id for r in budi_reservations):
                    print(f"✅ PASS: GET /api/reservations/mine?member_id={budi_id} does NOT contain Andi's reservation")
                else:
                    print(f"❌ FAIL: Andi's reservation incorrectly appears in Budi's query")
                    all_passed = False
            else:
                print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
                all_passed = False
        except Exception as e:
            print(f"❌ FAIL: Exception: {e}")
            all_passed = False
        
        # TEST 4: Siswa creates reservation for Budi
        print("\n--- TEST 4: Siswa POST /api/reservations with member_id (Budi) ---")
        try:
            resp = self.siswa_session.post(f"{BASE_URL}/reservations", json={
                "book_id": book2_id,
                "member_id": budi_id
            })
            if resp.status_code == 200:
                reservation = resp.json()
                self.test_data["reservations"].append(reservation)
                budi_res_id = reservation["id"]
                
                if reservation.get("member_name") == "Budi" and reservation.get("class_name") == "XII IPA 1":
                    print(f"✅ PASS: Reservation created with member_name='Budi', class_name='XII IPA 1'")
                    print(f"   Reservation ID: {budi_res_id}")
                else:
                    print(f"❌ FAIL: Expected member_name='Budi', class_name='XII IPA 1'")
                    print(f"   Got: member_name='{reservation.get('member_name')}', class_name='{reservation.get('class_name')}'")
                    all_passed = False
            else:
                print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
                all_passed = False
                budi_res_id = None
        except Exception as e:
            print(f"❌ FAIL: Exception: {e}")
            all_passed = False
            budi_res_id = None
        
        # TEST 5: DELETE with member_id validation
        print("\n--- TEST 5: Siswa DELETE /api/reservations with member_id validation ---")
        if andi_res_id:
            try:
                # 5a: Try to delete Andi's reservation with Budi's member_id (should fail 403)
                resp = self.siswa_session.delete(f"{BASE_URL}/reservations/{andi_res_id}?member_id={budi_id}")
                if resp.status_code == 403:
                    print(f"✅ PASS: DELETE with wrong member_id returns 403 (member mismatch)")
                else:
                    print(f"❌ FAIL: Expected 403, got {resp.status_code}: {resp.text}")
                    all_passed = False
                
                # 5b: Delete Andi's reservation with correct member_id (should succeed)
                resp = self.siswa_session.delete(f"{BASE_URL}/reservations/{andi_res_id}?member_id={andi_id}")
                if resp.status_code == 200:
                    print(f"✅ PASS: DELETE with correct member_id returns 200 (cancelled)")
                    
                    # Verify status is Dibatalkan
                    resp = self.admin_session.get(f"{BASE_URL}/reservations")
                    if resp.status_code == 200:
                        reservations = resp.json()
                        andi_res = next((r for r in reservations if r.get("id") == andi_res_id), None)
                        if andi_res and andi_res.get("status") == "Dibatalkan":
                            print(f"✅ PASS: Reservation status is 'Dibatalkan'")
                        else:
                            print(f"❌ FAIL: Expected status 'Dibatalkan', got '{andi_res.get('status') if andi_res else 'NOT FOUND'}'")
                            all_passed = False
                else:
                    print(f"❌ FAIL: Expected 200, got {resp.status_code}: {resp.text}")
                    all_passed = False
            except Exception as e:
                print(f"❌ FAIL: Exception: {e}")
                all_passed = False
        else:
            print("⚠ SKIP: Andi's reservation ID not available")
            all_passed = False
        
        # TEST 6: Backward compatibility - POST without member_id
        print("\n--- TEST 6: Backward compatibility - POST /api/reservations without member_id ---")
        try:
            # First, check if siswa account has a member record
            resp = self.siswa_session.get(f"{BASE_URL}/account/member")
            if resp.status_code == 200:
                siswa_member = resp.json()
                print(f"   Siswa account member: {siswa_member}")
            
            # Try to create reservation without member_id
            resp = self.siswa_session.post(f"{BASE_URL}/reservations", json={
                "book_id": book1_id  # Reuse book1 (Andi's reservation was cancelled)
            })
            
            if resp.status_code == 200:
                reservation = resp.json()
                self.test_data["reservations"].append(reservation)
                print(f"✅ PASS: POST without member_id returns 200 (backward compat)")
                print(f"   Recorded under member: {reservation.get('member_name')} (ID: {reservation.get('member_id')})")
            elif resp.status_code == 404:
                print(f"✅ PASS: POST without member_id returns 404 (siswa has no member record - acceptable)")
            else:
                print(f"⚠ INFO: POST without member_id returned {resp.status_code}: {resp.text}")
                # This is acceptable per requirements - just report the outcome
        except Exception as e:
            print(f"⚠ INFO: Exception during backward compat test: {e}")
        
        # Cleanup
        cleanup_success = self.cleanup()
        
        print("\n" + "="*70)
        if all_passed and cleanup_success:
            print("✅ ALL TESTS PASSED")
            print("="*70)
            return True
        else:
            print("❌ SOME TESTS FAILED")
            print("="*70)
            return False

def main():
    test_session = TestSession()
    success = test_session.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
