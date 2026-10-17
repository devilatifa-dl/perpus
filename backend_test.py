#!/usr/bin/env python3
"""
Backend Test Suite - Iteration 13: Post-Merge Conflict Resolution
Tests all core features after resolving merge conflicts from fitur/laporan-kartu-belakang-cetak-duplex
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Optional

# Base URL from frontend/.env
BASE_URL = "https://perpus-library-1.preview.emergentagent.com/api"

# Test credentials from test_credentials.md
ADMIN_CREDS = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
PETUGAS_CREDS = {"email": "petugas@smansa.sch.id", "password": "petugas123", "portal": "admin"}
SISWA_CREDS = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}

class TestSession:
    def __init__(self):
        self.admin_session = requests.Session()
        self.petugas_session = requests.Session()
        self.siswa_session = requests.Session()
        self.test_data = {
            "books": [],
            "members": [],
            "transactions": [],
            "visits": []
        }
        self.tests_passed = 0
        self.tests_failed = 0
    
    def login(self, session: requests.Session, creds: Dict) -> bool:
        """Login and store session cookie"""
        try:
            resp = session.post(f"{BASE_URL}/auth/login", json=creds)
            if resp.status_code == 200:
                user = resp.json()
                print(f"✓ Logged in as {user.get('name')} ({creds['email']}, portal={creds['portal']})")
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
    
    def test_auth_and_portal(self):
        """Test authentication and portal separation"""
        print("\n" + "="*70)
        print("TEST GROUP 1: Authentication & Portal Separation")
        print("="*70)
        
        # Test 1.1: Admin login on admin portal
        print("\n--- Test 1.1: Admin login on /admin portal ---")
        try:
            resp = requests.post(f"{BASE_URL}/auth/login", json=ADMIN_CREDS)
            self.test(
                "Admin login on admin portal returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                user = resp.json()
                self.test(
                    "Admin user has correct role",
                    user.get("role") == "admin",
                    f"Role: {user.get('role')}"
                )
                self.test(
                    "Admin user has correct name",
                    user.get("name") == "Devi Latifa, S.I.Pust",
                    f"Name: {user.get('name')}"
                )
        except Exception as e:
            self.test("Admin login", False, f"Exception: {e}")
        
        # Test 1.2: Petugas login on admin portal
        print("\n--- Test 1.2: Petugas login on /admin portal ---")
        try:
            resp = requests.post(f"{BASE_URL}/auth/login", json=PETUGAS_CREDS)
            self.test(
                "Petugas login on admin portal returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                user = resp.json()
                self.test(
                    "Petugas user has correct role",
                    user.get("role") == "petugas",
                    f"Role: {user.get('role')}"
                )
        except Exception as e:
            self.test("Petugas login", False, f"Exception: {e}")
        
        # Test 1.3: Siswa login on siswa portal
        print("\n--- Test 1.3: Siswa login on /siswa portal ---")
        try:
            resp = requests.post(f"{BASE_URL}/auth/login", json=SISWA_CREDS)
            self.test(
                "Siswa login on siswa portal returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                user = resp.json()
                self.test(
                    "Siswa user has correct role",
                    user.get("role") == "siswa",
                    f"Role: {user.get('role')}"
                )
        except Exception as e:
            self.test("Siswa login", False, f"Exception: {e}")
        
        # Test 1.4: Siswa cannot login on admin portal
        print("\n--- Test 1.4: Siswa cannot login on /admin portal ---")
        try:
            siswa_admin_creds = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "admin"}
            resp = requests.post(f"{BASE_URL}/auth/login", json=siswa_admin_creds)
            self.test(
                "Siswa login on admin portal returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa admin portal rejection", False, f"Exception: {e}")
        
        # Test 1.5: Admin cannot login on siswa portal
        print("\n--- Test 1.5: Admin cannot login on /siswa portal ---")
        try:
            admin_siswa_creds = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "siswa"}
            resp = requests.post(f"{BASE_URL}/auth/login", json=admin_siswa_creds)
            self.test(
                "Admin login on siswa portal returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Admin siswa portal rejection", False, f"Exception: {e}")
    
    def test_dashboard(self):
        """Test dashboard endpoint"""
        print("\n" + "="*70)
        print("TEST GROUP 2: Dashboard & Statistics")
        print("="*70)
        
        # Test 2.1: Admin dashboard
        print("\n--- Test 2.1: GET /api/dashboard (admin) ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/dashboard")
            self.test(
                "Dashboard returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                data = resp.json()
                required_fields = ["books", "titles", "available", "members", "borrowed", "missing", 
                                 "incoming", "transactions", "overdue", "reservations_waiting",
                                 "visitors_today", "visitors_inside"]
                has_all = all(field in data for field in required_fields)
                self.test(
                    "Dashboard has all required fields",
                    has_all,
                    f"Fields: {list(data.keys())}"
                )
        except Exception as e:
            self.test("Dashboard", False, f"Exception: {e}")
        
        # Test 2.2: Siswa dashboard (limited)
        print("\n--- Test 2.2: GET /api/dashboard (siswa) ---")
        try:
            resp = self.siswa_session.get(f"{BASE_URL}/dashboard")
            self.test(
                "Siswa dashboard returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                data = resp.json()
                self.test(
                    "Siswa dashboard has no visitor stats",
                    data.get("visitors_today") == 0 and data.get("visitors_inside") == 0,
                    f"visitors_today={data.get('visitors_today')}, visitors_inside={data.get('visitors_inside')}"
                )
        except Exception as e:
            self.test("Siswa dashboard", False, f"Exception: {e}")
    
    def test_books_crud(self):
        """Test books CRUD operations"""
        print("\n" + "="*70)
        print("TEST GROUP 3: Books CRUD Operations")
        print("="*70)
        
        # Test 3.1: List books
        print("\n--- Test 3.1: GET /api/books ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/books")
            self.test(
                "List books returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                books = resp.json()
                self.test(
                    "Books list is array",
                    isinstance(books, list),
                    f"Type: {type(books)}, Count: {len(books)}"
                )
                if books:
                    book = books[0]
                    required_fields = ["id", "title", "author", "category", "shelf", "stock", 
                                     "borrowed", "lost", "available", "status"]
                    has_all = all(field in book for field in required_fields)
                    self.test(
                        "Book has all required fields",
                        has_all,
                        f"Fields: {list(book.keys())}"
                    )
        except Exception as e:
            self.test("List books", False, f"Exception: {e}")
        
        # Test 3.2: Add book
        print("\n--- Test 3.2: POST /api/books ---")
        try:
            new_book = {
                "title": "Test Book Iteration 13",
                "author": "Test Author",
                "category": "Test",
                "shelf": "R-01",
                "isbn": "9781234567890",
                "cover": "",
                "stock": 2
            }
            resp = self.admin_session.post(f"{BASE_URL}/books", json=new_book)
            self.test(
                "Add book returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                book = resp.json()
                self.test_data["books"].append(book.get("id"))
                self.test(
                    "Added book has correct title",
                    book.get("title") == new_book["title"],
                    f"Title: {book.get('title')}"
                )
                self.test(
                    "Added book has correct stock",
                    book.get("stock") == new_book["stock"],
                    f"Stock: {book.get('stock')}"
                )
        except Exception as e:
            self.test("Add book", False, f"Exception: {e}")
        
        # Test 3.3: Update book
        print("\n--- Test 3.3: PUT /api/books/{id} ---")
        if self.test_data["books"]:
            try:
                book_id = self.test_data["books"][0]
                update_data = {
                    "title": "Updated Test Book",
                    "author": "Updated Author",
                    "category": "Test",
                    "shelf": "R-01",
                    "isbn": "9781234567890",
                    "cover": ""
                }
                resp = self.admin_session.put(f"{BASE_URL}/books/{book_id}", json=update_data)
                self.test(
                    "Update book returns 200",
                    resp.status_code == 200,
                    f"Status: {resp.status_code}"
                )
                if resp.status_code == 200:
                    book = resp.json()
                    self.test(
                        "Updated book has new title",
                        book.get("title") == update_data["title"],
                        f"Title: {book.get('title')}"
                    )
            except Exception as e:
                self.test("Update book", False, f"Exception: {e}")
        
        # Test 3.4: Adjust stock
        print("\n--- Test 3.4: PATCH /api/books/{id}/stock ---")
        if self.test_data["books"]:
            try:
                book_id = self.test_data["books"][0]
                resp = self.admin_session.patch(f"{BASE_URL}/books/{book_id}/stock", json={"stock": 5})
                self.test(
                    "Adjust stock returns 200",
                    resp.status_code == 200,
                    f"Status: {resp.status_code}"
                )
                if resp.status_code == 200:
                    book = resp.json()
                    self.test(
                        "Stock adjusted correctly",
                        book.get("stock") == 5,
                        f"Stock: {book.get('stock')}"
                    )
            except Exception as e:
                self.test("Adjust stock", False, f"Exception: {e}")
        
        # Test 3.5: Siswa cannot add book
        print("\n--- Test 3.5: Siswa cannot add book (403) ---")
        try:
            new_book = {
                "title": "Siswa Test Book",
                "author": "Siswa",
                "category": "Test",
                "shelf": "R-01",
                "isbn": "",
                "cover": "",
                "stock": 1
            }
            resp = self.siswa_session.post(f"{BASE_URL}/books", json=new_book)
            self.test(
                "Siswa add book returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa add book rejection", False, f"Exception: {e}")
    
    def test_members_crud(self):
        """Test members CRUD operations"""
        print("\n" + "="*70)
        print("TEST GROUP 4: Members CRUD Operations")
        print("="*70)
        
        # Test 4.1: List members
        print("\n--- Test 4.1: GET /api/members ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/members")
            self.test(
                "List members returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                members = resp.json()
                self.test(
                    "Members list is array",
                    isinstance(members, list),
                    f"Type: {type(members)}, Count: {len(members)}"
                )
                if members:
                    member = members[0]
                    required_fields = ["id", "name", "student_id", "class_name", "photo"]
                    has_all = all(field in member for field in required_fields)
                    self.test(
                        "Member has all required fields",
                        has_all,
                        f"Fields: {list(member.keys())}"
                    )
        except Exception as e:
            self.test("List members", False, f"Exception: {e}")
        
        # Test 4.2: Add member
        print("\n--- Test 4.2: POST /api/members ---")
        try:
            new_member = {
                "name": "Test Member Iteration 13",
                "student_id": "99999",
                "class_name": "XII IPA 1",
                "photo": ""
            }
            resp = self.admin_session.post(f"{BASE_URL}/members", json=new_member)
            self.test(
                "Add member returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                member = resp.json()
                self.test_data["members"].append(member.get("id"))
                self.test(
                    "Added member has correct name",
                    member.get("name") == new_member["name"],
                    f"Name: {member.get('name')}"
                )
        except Exception as e:
            self.test("Add member", False, f"Exception: {e}")
        
        # Test 4.3: Update member
        print("\n--- Test 4.3: PUT /api/members/{id} ---")
        if self.test_data["members"]:
            try:
                member_id = self.test_data["members"][0]
                update_data = {
                    "name": "Updated Test Member",
                    "student_id": "99999",
                    "class_name": "XII IPA 2",
                    "photo": ""
                }
                resp = self.admin_session.put(f"{BASE_URL}/members/{member_id}", json=update_data)
                self.test(
                    "Update member returns 200",
                    resp.status_code == 200,
                    f"Status: {resp.status_code}"
                )
                if resp.status_code == 200:
                    member = resp.json()
                    self.test(
                        "Updated member has new class",
                        member.get("class_name") == update_data["class_name"],
                        f"Class: {member.get('class_name')}"
                    )
            except Exception as e:
                self.test("Update member", False, f"Exception: {e}")
        
        # Test 4.4: Siswa cannot add member
        print("\n--- Test 4.4: Siswa cannot add member (403) ---")
        try:
            new_member = {
                "name": "Siswa Test Member",
                "student_id": "88888",
                "class_name": "X IPA 1",
                "photo": ""
            }
            resp = self.siswa_session.post(f"{BASE_URL}/members", json=new_member)
            self.test(
                "Siswa add member returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa add member rejection", False, f"Exception: {e}")
    
    def test_member_import(self):
        """Test member import with Excel template"""
        print("\n" + "="*70)
        print("TEST GROUP 5: Member Import (Excel Template)")
        print("="*70)
        
        # Test 5.1: Download Excel template
        print("\n--- Test 5.1: GET /api/members/import-template.xlsx ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/members/import-template.xlsx")
            self.test(
                "Download template returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                self.test(
                    "Template is Excel file",
                    resp.headers.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    f"Content-Type: {resp.headers.get('Content-Type')}"
                )
        except Exception as e:
            self.test("Download template", False, f"Exception: {e}")
        
        # Test 5.2: Siswa cannot download template
        print("\n--- Test 5.2: Siswa cannot download template (403) ---")
        try:
            resp = self.siswa_session.get(f"{BASE_URL}/members/import-template.xlsx")
            self.test(
                "Siswa download template returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa template rejection", False, f"Exception: {e}")
    
    def test_circulation(self):
        """Test circulation (borrow/return)"""
        print("\n" + "="*70)
        print("TEST GROUP 6: Circulation (Borrow/Return)")
        print("="*70)
        
        # Test 6.1: List transactions
        print("\n--- Test 6.1: GET /api/transactions ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/transactions")
            self.test(
                "List transactions returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                transactions = resp.json()
                self.test(
                    "Transactions list is array",
                    isinstance(transactions, list),
                    f"Type: {type(transactions)}, Count: {len(transactions)}"
                )
        except Exception as e:
            self.test("List transactions", False, f"Exception: {e}")
        
        # Test 6.2: Borrow book (if we have test data)
        print("\n--- Test 6.2: POST /api/transactions (borrow) ---")
        if self.test_data["books"] and self.test_data["members"]:
            try:
                transaction_data = {
                    "member_id": self.test_data["members"][0],
                    "book_id": self.test_data["books"][0],
                    "action": "pinjam"
                }
                resp = self.admin_session.post(f"{BASE_URL}/transactions", json=transaction_data)
                self.test(
                    "Borrow book returns 200",
                    resp.status_code == 200,
                    f"Status: {resp.status_code}"
                )
                if resp.status_code == 200:
                    transaction = resp.json()
                    self.test_data["transactions"].append(transaction.get("id"))
                    self.test(
                        "Transaction has correct action",
                        transaction.get("action") == "pinjam",
                        f"Action: {transaction.get('action')}"
                    )
            except Exception as e:
                self.test("Borrow book", False, f"Exception: {e}")
        
        # Test 6.3: Return book
        print("\n--- Test 6.3: POST /api/transactions (return) ---")
        if self.test_data["books"] and self.test_data["members"]:
            try:
                transaction_data = {
                    "member_id": self.test_data["members"][0],
                    "book_id": self.test_data["books"][0],
                    "action": "kembali"
                }
                resp = self.admin_session.post(f"{BASE_URL}/transactions", json=transaction_data)
                self.test(
                    "Return book returns 200",
                    resp.status_code == 200,
                    f"Status: {resp.status_code}"
                )
                if resp.status_code == 200:
                    transaction = resp.json()
                    self.test(
                        "Transaction has correct action",
                        transaction.get("action") == "kembali",
                        f"Action: {transaction.get('action')}"
                    )
            except Exception as e:
                self.test("Return book", False, f"Exception: {e}")
        
        # Test 6.4: Siswa cannot create transaction
        print("\n--- Test 6.4: Siswa cannot create transaction (403) ---")
        try:
            transaction_data = {
                "member_id": "MB-2024001",
                "book_id": "BK-1042",
                "action": "pinjam"
            }
            resp = self.siswa_session.post(f"{BASE_URL}/transactions", json=transaction_data)
            self.test(
                "Siswa create transaction returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa transaction rejection", False, f"Exception: {e}")
    
    def test_reports(self):
        """Test reports endpoints"""
        print("\n" + "="*70)
        print("TEST GROUP 7: Reports (PDF/Excel Export)")
        print("="*70)
        
        # Test 7.1: Get reports data
        print("\n--- Test 7.1: GET /api/reports ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/reports")
            self.test(
                "Get reports returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                data = resp.json()
                required_fields = ["transactions", "loans", "incoming", "missing"]
                has_all = all(field in data for field in required_fields)
                self.test(
                    "Reports has all required fields",
                    has_all,
                    f"Fields: {list(data.keys())}"
                )
        except Exception as e:
            self.test("Get reports", False, f"Exception: {e}")
        
        # Test 7.2: Export PDF (transaksi)
        print("\n--- Test 7.2: GET /api/reports/export.pdf?type=transaksi ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/reports/export.pdf", params={"type": "transaksi", "period": "semua"})
            self.test(
                "Export PDF returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                self.test(
                    "PDF has correct content type",
                    resp.headers.get("Content-Type") == "application/pdf",
                    f"Content-Type: {resp.headers.get('Content-Type')}"
                )
        except Exception as e:
            self.test("Export PDF", False, f"Exception: {e}")
        
        # Test 7.3: Export Excel (transaksi)
        print("\n--- Test 7.3: GET /api/reports/export.xlsx?type=transaksi ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/reports/export.xlsx", params={"type": "transaksi", "period": "semua"})
            self.test(
                "Export Excel returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                self.test(
                    "Excel has correct content type",
                    resp.headers.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    f"Content-Type: {resp.headers.get('Content-Type')}"
                )
        except Exception as e:
            self.test("Export Excel", False, f"Exception: {e}")
        
        # Test 7.4: Siswa cannot access reports
        print("\n--- Test 7.4: Siswa cannot access reports (403) ---")
        try:
            resp = self.siswa_session.get(f"{BASE_URL}/reports")
            self.test(
                "Siswa get reports returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa reports rejection", False, f"Exception: {e}")
    
    def test_settings_photo_upload(self):
        """Test settings endpoints for photo upload"""
        print("\n" + "="*70)
        print("TEST GROUP 8: Settings (Photo Upload)")
        print("="*70)
        
        # Test 8.1: Get settings
        print("\n--- Test 8.1: GET /api/settings ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/settings")
            self.test(
                "Get settings returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                settings = resp.json()
                self.test(
                    "Settings has member_photo_upload field",
                    "member_photo_upload" in settings,
                    f"member_photo_upload: {settings.get('member_photo_upload')}"
                )
        except Exception as e:
            self.test("Get settings", False, f"Exception: {e}")
        
        # Test 8.2: Get student photo settings
        print("\n--- Test 8.2: GET /api/settings/student-photo ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/settings/student-photo")
            self.test(
                "Get student photo settings returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                config = resp.json()
                required_fields = ["enabled", "until", "allow_replace", "open"]
                has_all = all(field in config for field in required_fields)
                self.test(
                    "Student photo config has all required fields",
                    has_all,
                    f"Fields: {list(config.keys())}"
                )
        except Exception as e:
            self.test("Get student photo settings", False, f"Exception: {e}")
        
        # Test 8.3: Update student photo settings (admin)
        print("\n--- Test 8.3: PUT /api/settings/student-photo (admin) ---")
        try:
            config_data = {
                "enabled": True,
                "until": "",
                "allow_replace": True
            }
            resp = self.admin_session.put(f"{BASE_URL}/settings/student-photo", json=config_data)
            self.test(
                "Update student photo settings returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                config = resp.json()
                self.test(
                    "Updated config has correct enabled value",
                    config.get("enabled") == True,
                    f"enabled: {config.get('enabled')}"
                )
        except Exception as e:
            self.test("Update student photo settings", False, f"Exception: {e}")
        
        # Test 8.4: Siswa cannot update settings
        print("\n--- Test 8.4: Siswa cannot update settings (403) ---")
        try:
            config_data = {
                "enabled": False,
                "until": "",
                "allow_replace": False
            }
            resp = self.siswa_session.put(f"{BASE_URL}/settings/student-photo", json=config_data)
            self.test(
                "Siswa update settings returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa settings rejection", False, f"Exception: {e}")
    
    def test_shelves(self):
        """Test shelves endpoints"""
        print("\n" + "="*70)
        print("TEST GROUP 9: Shelves (Rak Buku)")
        print("="*70)
        
        # Test 9.1: List shelves
        print("\n--- Test 9.1: GET /api/shelves ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/shelves")
            self.test(
                "List shelves returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                shelves = resp.json()
                self.test(
                    "Shelves list is array",
                    isinstance(shelves, list),
                    f"Type: {type(shelves)}, Count: {len(shelves)}"
                )
                if shelves:
                    shelf = shelves[0]
                    required_fields = ["id", "name", "capacity", "color"]
                    has_all = all(field in shelf for field in required_fields)
                    self.test(
                        "Shelf has all required fields",
                        has_all,
                        f"Fields: {list(shelf.keys())}"
                    )
        except Exception as e:
            self.test("List shelves", False, f"Exception: {e}")
    
    def test_visitors(self):
        """Test visitors endpoints"""
        print("\n" + "="*70)
        print("TEST GROUP 10: Visitors (Pengunjung)")
        print("="*70)
        
        # Test 10.1: Get visits
        print("\n--- Test 10.1: GET /api/visits ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/visits")
            self.test(
                "Get visits returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            if resp.status_code == 200:
                data = resp.json()
                required_fields = ["date", "checkout_time", "items", "summary"]
                has_all = all(field in data for field in required_fields)
                self.test(
                    "Visits data has all required fields",
                    has_all,
                    f"Fields: {list(data.keys())}"
                )
        except Exception as e:
            self.test("Get visits", False, f"Exception: {e}")
        
        # Test 10.2: Siswa cannot access visits
        print("\n--- Test 10.2: Siswa cannot access visits (403) ---")
        try:
            resp = self.siswa_session.get(f"{BASE_URL}/visits")
            self.test(
                "Siswa get visits returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa visits rejection", False, f"Exception: {e}")
    
    def cleanup(self) -> bool:
        """Delete test data created during testing"""
        print("\n=== CLEANUP: Removing Test Data ===")
        success = True
        
        # Delete test books
        for book_id in self.test_data["books"]:
            try:
                resp = self.admin_session.delete(f"{BASE_URL}/books/{book_id}")
                if resp.status_code in [200, 404]:
                    print(f"✓ Deleted book {book_id}")
                else:
                    print(f"✗ Failed to delete book {book_id}: {resp.status_code}")
                    success = False
            except Exception as e:
                print(f"✗ Error deleting book {book_id}: {e}")
                success = False
        
        # Delete test members
        for member_id in self.test_data["members"]:
            try:
                resp = self.admin_session.delete(f"{BASE_URL}/members/{member_id}")
                if resp.status_code in [200, 404]:
                    print(f"✓ Deleted member {member_id}")
                else:
                    print(f"✗ Failed to delete member {member_id}: {resp.status_code}")
                    success = False
            except Exception as e:
                print(f"✗ Error deleting member {member_id}: {e}")
                success = False
        
        return success
    
    def run_tests(self) -> bool:
        """Run all test groups"""
        print("\n" + "="*70)
        print("ITERATION 13 BACKEND TESTS: Post-Merge Conflict Resolution")
        print("Testing: Auth, Dashboard, Books, Members, Import, Circulation, Reports, Settings")
        print("="*70)
        
        # Login
        if not self.login(self.admin_session, ADMIN_CREDS):
            return False
        if not self.login(self.petugas_session, PETUGAS_CREDS):
            return False
        if not self.login(self.siswa_session, SISWA_CREDS):
            return False
        
        # Run test groups
        self.test_auth_and_portal()
        self.test_dashboard()
        self.test_books_crud()
        self.test_members_crud()
        self.test_member_import()
        self.test_circulation()
        self.test_reports()
        self.test_settings_photo_upload()
        self.test_shelves()
        self.test_visitors()
        
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
