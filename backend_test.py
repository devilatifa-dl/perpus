#!/usr/bin/env python3
"""
Backend Test Suite - Round 8: Leaderboard, Edit Book, Shelves, Text Rename
Tests new features: visit leaderboard, book editing, shelf management, and text changes.
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional

# Base URL from frontend/.env
BASE_URL = "https://perpus-app-8.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
PETUGAS_CREDS = {"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"}
SISWA_CREDS = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}

class TestSession:
    def __init__(self):
        self.admin_session = requests.Session()
        self.petugas_session = requests.Session()
        self.siswa_session = requests.Session()
        self.test_data = {
            "members": [],
            "books": [],
            "shelves": [],
            "visits": [],
            "original_books": {}  # Store original book data for restoration
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
    
    def setup_test_data(self) -> bool:
        """Create test members and ensure sample visits exist"""
        print("\n=== SETUP: Preparing Test Data ===")
        
        # Get existing members (Raka, Bima, Siti should exist from seed)
        try:
            resp = self.admin_session.get(f"{BASE_URL}/members")
            if resp.status_code == 200:
                members = resp.json()
                print(f"✓ Found {len(members)} existing members")
                self.test_data["members"] = members
            else:
                print(f"✗ Failed to get members: {resp.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error getting members: {e}")
            return False
        
        # Get existing books
        try:
            resp = self.admin_session.get(f"{BASE_URL}/books")
            if resp.status_code == 200:
                books = resp.json()
                print(f"✓ Found {len(books)} existing books")
                self.test_data["books"] = books
                # Store original data for books we'll edit
                for book in books[:2]:  # Store first 2 books
                    self.test_data["original_books"][book["id"]] = {
                        "title": book["title"],
                        "author": book["author"],
                        "category": book.get("category", "Umum"),
                        "shelf": book["shelf"],
                        "isbn": book.get("isbn", ""),
                        "cover": book.get("cover", "")
                    }
            else:
                print(f"✗ Failed to get books: {resp.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error getting books: {e}")
            return False
        
        # Get existing shelves
        try:
            resp = self.admin_session.get(f"{BASE_URL}/shelves")
            if resp.status_code == 200:
                shelves = resp.json()
                print(f"✓ Found {len(shelves)} existing shelves")
                self.test_data["shelves"] = shelves
            else:
                print(f"✗ Failed to get shelves: {resp.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error getting shelves: {e}")
            return False
        
        print(f"✓ Setup complete")
        return True
    
    def cleanup(self) -> bool:
        """Restore original data"""
        print("\n=== CLEANUP: Restoring Original Data ===")
        success = True
        
        # Restore edited books
        for book_id, original in self.test_data["original_books"].items():
            try:
                resp = self.admin_session.put(f"{BASE_URL}/books/{book_id}", json=original)
                if resp.status_code == 200:
                    print(f"✓ Restored book {book_id}")
                else:
                    print(f"✗ Failed to restore book {book_id}: {resp.status_code}")
                    success = False
            except Exception as e:
                print(f"✗ Error restoring book {book_id}: {e}")
                success = False
        
        # Delete test shelves (those created during tests)
        for shelf in self.test_data["shelves"]:
            if shelf["id"].startswith("TEST-"):
                try:
                    # Move books if any
                    resp = self.admin_session.get(f"{BASE_URL}/books")
                    if resp.status_code == 200:
                        books = resp.json()
                        books_on_shelf = [b for b in books if b["shelf"] == shelf["id"]]
                        if books_on_shelf:
                            # Move to R-01
                            resp = self.admin_session.delete(f"{BASE_URL}/shelves/{shelf['id']}", params={"move_to": "R-01"})
                        else:
                            resp = self.admin_session.delete(f"{BASE_URL}/shelves/{shelf['id']}")
                        
                        if resp.status_code in [200, 404]:
                            print(f"✓ Deleted test shelf {shelf['id']}")
                        else:
                            print(f"✗ Failed to delete shelf {shelf['id']}: {resp.status_code}")
                            success = False
                except Exception as e:
                    print(f"✗ Error deleting shelf {shelf['id']}: {e}")
                    success = False
        
        return success
    
    def test_leaderboard_backend(self):
        """Test leaderboard API endpoints"""
        print("\n" + "="*70)
        print("TEST GROUP 1: Leaderboard Backend API")
        print("="*70)
        
        # Test 1.1: GET /api/visits/leaderboard without month (current month)
        print("\n--- Test 1.1: GET /api/visits/leaderboard (current month) ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/leaderboard")
            self.test(
                "Leaderboard returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                data = resp.json()
                required_fields = ["month", "label", "total_visits", "active_students", "students", "classes", "months"]
                has_all_fields = all(field in data for field in required_fields)
                self.test(
                    "Leaderboard has all required fields",
                    has_all_fields,
                    f"Fields: {list(data.keys())}"
                )
                
                # Check students structure
                if data.get("students"):
                    student = data["students"][0]
                    student_fields = ["rank", "name", "class_name", "visits", "days", "pct"]
                    has_student_fields = all(field in student for field in student_fields)
                    self.test(
                        "Student entry has correct structure",
                        has_student_fields,
                        f"Fields: {list(student.keys())}"
                    )
                    
                    # Siswa role should not see 'minutes' field
                    self.test(
                        "Admin sees 'minutes' field in student data",
                        "minutes" in student,
                        f"Has minutes: {'minutes' in student}"
                    )
                
                # Check classes structure
                if data.get("classes"):
                    cls = data["classes"][0]
                    class_fields = ["rank", "class_name", "visits", "members", "pct"]
                    has_class_fields = all(field in cls for field in class_fields)
                    self.test(
                        "Class entry has correct structure",
                        has_class_fields,
                        f"Fields: {list(cls.keys())}"
                    )
        except Exception as e:
            self.test("Leaderboard API call", False, f"Exception: {e}")
        
        # Test 1.2: GET /api/visits/leaderboard with specific month
        print("\n--- Test 1.2: GET /api/visits/leaderboard?month=YYYY-MM ---")
        try:
            current_month = datetime.now().strftime("%Y-%m")
            resp = self.admin_session.get(f"{BASE_URL}/visits/leaderboard", params={"month": current_month})
            self.test(
                "Leaderboard with month parameter returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                data = resp.json()
                self.test(
                    "Leaderboard month matches requested month",
                    data.get("month") == current_month,
                    f"Requested: {current_month}, Got: {data.get('month')}"
                )
        except Exception as e:
            self.test("Leaderboard with month parameter", False, f"Exception: {e}")
        
        # Test 1.3: Invalid month format returns 400
        print("\n--- Test 1.3: GET /api/visits/leaderboard?month=invalid ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/leaderboard", params={"month": "invalid"})
            self.test(
                "Invalid month format returns 400",
                resp.status_code == 400,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Invalid month format", False, f"Exception: {e}")
        
        # Test 1.4: Siswa can access leaderboard (no minutes field)
        print("\n--- Test 1.4: Siswa GET /api/visits/leaderboard ---")
        try:
            resp = self.siswa_session.get(f"{BASE_URL}/visits/leaderboard")
            self.test(
                "Siswa can access leaderboard",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("students"):
                    student = data["students"][0]
                    self.test(
                        "Siswa does NOT see 'minutes' field",
                        "minutes" not in student,
                        f"Has minutes: {'minutes' in student}"
                    )
        except Exception as e:
            self.test("Siswa leaderboard access", False, f"Exception: {e}")
        
        # Test 1.5: Export leaderboard PDF (staff only)
        print("\n--- Test 1.5: GET /api/reports/export.pdf?type=peringkat ---")
        try:
            current_month = datetime.now().strftime("%Y-%m")
            resp = self.admin_session.get(f"{BASE_URL}/reports/export.pdf", params={"type": "peringkat", "period": current_month})
            self.test(
                "Export leaderboard PDF returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}, Content-Type: {resp.headers.get('Content-Type')}"
            )
            
            self.test(
                "PDF has correct content type",
                resp.headers.get("Content-Type") == "application/pdf",
                f"Content-Type: {resp.headers.get('Content-Type')}"
            )
        except Exception as e:
            self.test("Export leaderboard PDF", False, f"Exception: {e}")
        
        # Test 1.6: Export leaderboard Excel (staff only)
        print("\n--- Test 1.6: GET /api/reports/export.xlsx?type=peringkat ---")
        try:
            current_month = datetime.now().strftime("%Y-%m")
            resp = self.admin_session.get(f"{BASE_URL}/reports/export.xlsx", params={"type": "peringkat", "period": current_month})
            self.test(
                "Export leaderboard Excel returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            self.test(
                "Excel has correct content type",
                "spreadsheet" in resp.headers.get("Content-Type", ""),
                f"Content-Type: {resp.headers.get('Content-Type')}"
            )
        except Exception as e:
            self.test("Export leaderboard Excel", False, f"Exception: {e}")
    
    def test_edit_book(self):
        """Test book editing functionality"""
        print("\n" + "="*70)
        print("TEST GROUP 2: Edit Book")
        print("="*70)
        
        if not self.test_data["books"]:
            print("⚠ SKIP: No books available for testing")
            return
        
        book = self.test_data["books"][0]
        book_id = book["id"]
        
        # Test 2.1: Edit book with valid data
        print(f"\n--- Test 2.1: PUT /api/books/{book_id} (valid edit) ---")
        try:
            edit_data = {
                "title": book["title"] + " (Edited)",
                "author": book["author"],
                "category": book.get("category", "Umum"),
                "shelf": book["shelf"],
                "isbn": book.get("isbn", ""),
                "cover": book.get("cover", "")
            }
            resp = self.admin_session.put(f"{BASE_URL}/books/{book_id}", json=edit_data)
            self.test(
                "Edit book returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                updated = resp.json()
                self.test(
                    "Book title updated correctly",
                    updated["title"] == edit_data["title"],
                    f"Expected: {edit_data['title']}, Got: {updated['title']}"
                )
        except Exception as e:
            self.test("Edit book", False, f"Exception: {e}")
        
        # Test 2.2: Edit book with invalid shelf
        print(f"\n--- Test 2.2: PUT /api/books/{book_id} (invalid shelf) ---")
        try:
            edit_data = {
                "title": book["title"],
                "author": book["author"],
                "category": book.get("category", "Umum"),
                "shelf": "INVALID-SHELF-999",
                "isbn": book.get("isbn", ""),
                "cover": book.get("cover", "")
            }
            resp = self.admin_session.put(f"{BASE_URL}/books/{book_id}", json=edit_data)
            self.test(
                "Invalid shelf returns 400",
                resp.status_code == 400,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 400:
                error = resp.json().get("detail", "")
                self.test(
                    "Error message mentions 'Rak tidak ditemukan'",
                    "Rak tidak ditemukan" in error,
                    f"Error: {error}"
                )
        except Exception as e:
            self.test("Invalid shelf validation", False, f"Exception: {e}")
        
        # Test 2.3: Edit book with duplicate title+author
        print(f"\n--- Test 2.3: PUT /api/books/{book_id} (duplicate title+author) ---")
        if len(self.test_data["books"]) >= 2:
            try:
                other_book = self.test_data["books"][1]
                edit_data = {
                    "title": other_book["title"],
                    "author": other_book["author"],
                    "category": book.get("category", "Umum"),
                    "shelf": book["shelf"],
                    "isbn": book.get("isbn", ""),
                    "cover": book.get("cover", "")
                }
                resp = self.admin_session.put(f"{BASE_URL}/books/{book_id}", json=edit_data)
                self.test(
                    "Duplicate title+author returns 400",
                    resp.status_code == 400,
                    f"Status: {resp.status_code}"
                )
                
                if resp.status_code == 400:
                    error = resp.json().get("detail", "")
                    self.test(
                        "Error message mentions duplicate",
                        "sudah ada" in error.lower(),
                        f"Error: {error}"
                    )
            except Exception as e:
                self.test("Duplicate title+author validation", False, f"Exception: {e}")
        else:
            print("⚠ SKIP: Need at least 2 books for duplicate test")
        
        # Test 2.4: Siswa cannot edit book (403)
        print(f"\n--- Test 2.4: Siswa PUT /api/books/{book_id} (forbidden) ---")
        try:
            edit_data = {
                "title": book["title"],
                "author": book["author"],
                "category": book.get("category", "Umum"),
                "shelf": book["shelf"],
                "isbn": book.get("isbn", ""),
                "cover": book.get("cover", "")
            }
            resp = self.siswa_session.put(f"{BASE_URL}/books/{book_id}", json=edit_data)
            self.test(
                "Siswa cannot edit book (403)",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa edit book forbidden", False, f"Exception: {e}")
        
        # Restore original book data
        print(f"\n--- Restoring original book data ---")
        try:
            original = self.test_data["original_books"][book_id]
            resp = self.admin_session.put(f"{BASE_URL}/books/{book_id}", json=original)
            if resp.status_code == 200:
                print(f"✓ Restored book {book_id} to original state")
        except Exception as e:
            print(f"✗ Failed to restore book: {e}")
    
    def test_shelves_crud(self):
        """Test shelf CRUD operations"""
        print("\n" + "="*70)
        print("TEST GROUP 3: Shelves CRUD")
        print("="*70)
        
        # Test 3.1: Create new shelf
        print("\n--- Test 3.1: POST /api/shelves (create) ---")
        test_shelf_id = "TEST-01"
        try:
            shelf_data = {
                "id": test_shelf_id,
                "name": "Test Shelf",
                "capacity": 100,
                "color": "azure"
            }
            resp = self.admin_session.post(f"{BASE_URL}/shelves", json=shelf_data)
            self.test(
                "Create shelf returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                created = resp.json()
                self.test_data["shelves"].append(created)
                self.test(
                    "Shelf created with correct ID",
                    created["id"] == test_shelf_id,
                    f"Expected: {test_shelf_id}, Got: {created['id']}"
                )
        except Exception as e:
            self.test("Create shelf", False, f"Exception: {e}")
        
        # Test 3.2: Create shelf with duplicate ID (should fail)
        print("\n--- Test 3.2: POST /api/shelves (duplicate ID) ---")
        try:
            shelf_data = {
                "id": test_shelf_id,
                "name": "Duplicate Shelf",
                "capacity": 50,
                "color": "mint"
            }
            resp = self.admin_session.post(f"{BASE_URL}/shelves", json=shelf_data)
            self.test(
                "Duplicate shelf ID returns 400",
                resp.status_code == 400,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 400:
                error = resp.json().get("detail", "")
                self.test(
                    "Error message mentions duplicate",
                    "sudah dipakai" in error.lower(),
                    f"Error: {error}"
                )
        except Exception as e:
            self.test("Duplicate shelf ID validation", False, f"Exception: {e}")
        
        # Test 3.3: Edit shelf (rename code)
        print(f"\n--- Test 3.3: PUT /api/shelves/{test_shelf_id} (rename code) ---")
        new_shelf_id = "TEST-02"
        try:
            shelf_data = {
                "id": new_shelf_id,
                "name": "Test Shelf Renamed",
                "capacity": 120,
                "color": "amber"
            }
            resp = self.admin_session.put(f"{BASE_URL}/shelves/{test_shelf_id}", json=shelf_data)
            self.test(
                "Edit shelf returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                updated = resp.json()
                self.test(
                    "Shelf code updated correctly",
                    updated["id"] == new_shelf_id,
                    f"Expected: {new_shelf_id}, Got: {updated['id']}"
                )
                # Update test_shelf_id for cleanup
                test_shelf_id = new_shelf_id
        except Exception as e:
            self.test("Edit shelf", False, f"Exception: {e}")
        
        # Test 3.4: Delete empty shelf
        print(f"\n--- Test 3.4: DELETE /api/shelves/{test_shelf_id} (empty shelf) ---")
        try:
            resp = self.admin_session.delete(f"{BASE_URL}/shelves/{test_shelf_id}")
            self.test(
                "Delete empty shelf returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Delete empty shelf", False, f"Exception: {e}")
        
        # Test 3.5: Cannot delete last shelf
        print("\n--- Test 3.5: DELETE last shelf (should fail) ---")
        try:
            # Get all shelves
            resp = self.admin_session.get(f"{BASE_URL}/shelves")
            if resp.status_code == 200:
                shelves = resp.json()
                if len(shelves) == 1:
                    last_shelf = shelves[0]
                    resp = self.admin_session.delete(f"{BASE_URL}/shelves/{last_shelf['id']}")
                    self.test(
                        "Cannot delete last shelf (400)",
                        resp.status_code == 400,
                        f"Status: {resp.status_code}"
                    )
                else:
                    print(f"⚠ SKIP: More than 1 shelf exists ({len(shelves)}), cannot test last shelf deletion")
        except Exception as e:
            self.test("Delete last shelf validation", False, f"Exception: {e}")
        
        # Test 3.6: Siswa cannot create/edit/delete shelves (403)
        print("\n--- Test 3.6: Siswa shelf operations (forbidden) ---")
        try:
            shelf_data = {"id": "TEST-SISWA", "name": "Siswa Shelf", "capacity": 50, "color": "azure"}
            resp = self.siswa_session.post(f"{BASE_URL}/shelves", json=shelf_data)
            self.test(
                "Siswa cannot create shelf (403)",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa create shelf forbidden", False, f"Exception: {e}")
    
    def test_regression(self):
        """Test that existing features still work"""
        print("\n" + "="*70)
        print("TEST GROUP 4: Regression Tests")
        print("="*70)
        
        # Test 4.1: Visitor scan still works
        print("\n--- Test 4.1: POST /api/visits/scan (visitor check-in) ---")
        if self.test_data["members"]:
            try:
                member = self.test_data["members"][0]
                resp = self.admin_session.post(f"{BASE_URL}/visits/scan", json={"code": member["id"]})
                self.test(
                    "Visitor scan returns 200",
                    resp.status_code == 200,
                    f"Status: {resp.status_code}"
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    self.test(
                        "Scan result has action field",
                        "action" in result,
                        f"Action: {result.get('action')}"
                    )
            except Exception as e:
                self.test("Visitor scan", False, f"Exception: {e}")
        else:
            print("⚠ SKIP: No members available for visitor scan test")
        
        # Test 4.2: Circulation (borrow/return) still works
        print("\n--- Test 4.2: POST /api/transactions (circulation) ---")
        if self.test_data["members"] and self.test_data["books"]:
            try:
                member = self.test_data["members"][0]
                book = next((b for b in self.test_data["books"] if b.get("available", 0) > 0), None)
                
                if book:
                    # Try to borrow
                    resp = self.admin_session.post(f"{BASE_URL}/transactions", json={
                        "member_id": member["id"],
                        "book_id": book["id"],
                        "action": "pinjam"
                    })
                    
                    # May fail if already borrowed, that's ok
                    if resp.status_code == 200:
                        self.test("Circulation borrow works", True, "Successfully borrowed book")
                        
                        # Try to return
                        resp = self.admin_session.post(f"{BASE_URL}/transactions", json={
                            "member_id": member["id"],
                            "book_id": book["id"],
                            "action": "kembali"
                        })
                        self.test(
                            "Circulation return works",
                            resp.status_code == 200,
                            f"Status: {resp.status_code}"
                        )
                    elif resp.status_code == 400:
                        print(f"⚠ INFO: Cannot borrow (already borrowed or no stock): {resp.json().get('detail')}")
                    else:
                        self.test("Circulation borrow", False, f"Status: {resp.status_code}")
                else:
                    print("⚠ SKIP: No available books for circulation test")
            except Exception as e:
                self.test("Circulation", False, f"Exception: {e}")
        else:
            print("⚠ SKIP: No members or books available for circulation test")
        
        # Test 4.3: Visit stats still works
        print("\n--- Test 4.3: GET /api/visits/stats (statistics) ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits/stats", params={"period": "7hari"})
            self.test(
                "Visit stats returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                stats = resp.json()
                required_fields = ["period", "total", "per_day", "per_class", "per_hour"]
                has_fields = all(field in stats for field in required_fields)
                self.test(
                    "Stats has required fields",
                    has_fields,
                    f"Fields: {list(stats.keys())}"
                )
        except Exception as e:
            self.test("Visit stats", False, f"Exception: {e}")
    
    def run_tests(self) -> bool:
        """Run all test groups"""
        print("\n" + "="*70)
        print("ROUND 8 BACKEND TESTS: Leaderboard, Edit Book, Shelves, Text Rename")
        print("="*70)
        
        # Login
        if not self.login(self.admin_session, ADMIN_CREDS):
            return False
        if not self.login(self.petugas_session, PETUGAS_CREDS):
            return False
        if not self.login(self.siswa_session, SISWA_CREDS):
            return False
        
        # Setup
        if not self.setup_test_data():
            return False
        
        # Run test groups
        self.test_leaderboard_backend()
        self.test_edit_book()
        self.test_shelves_crud()
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
