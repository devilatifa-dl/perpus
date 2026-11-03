#!/usr/bin/env python3
"""
Backend Test Suite - Iteration 23: Performance & Backup Improvements
Tests:
1. Single backup button (merged backup-json and backup-zip into one)
2. Performance: GET /api/books returns small response (~35KB vs 24MB)
3. Book covers as URLs instead of base64
4. GZip compression for JSON APIs
5. Book cover endpoint with caching headers
"""

import requests
import json
import sys
import gzip
from datetime import datetime
from typing import Dict

# Base URL from frontend/.env
BASE_URL = "https://perpus-devilatifa--369vmy1r.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@smansa.sch.id", "password": "admin123", "portal": "admin"}
SISWA_CREDS = {"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"}

class TestSession:
    def __init__(self):
        self.admin_session = requests.Session()
        self.siswa_session = requests.Session()
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_book_id = None
    
    def login(self, session: requests.Session, creds: Dict) -> bool:
        """Login and store session cookie"""
        try:
            resp = session.post(f"{BASE_URL}/auth/login", json=creds)
            if resp.status_code == 200:
                user = resp.json()
                print(f"✓ Logged in as {user.get('name')} ({creds['email']})")
                return True
            else:
                print(f"✗ Login failed for {creds['email']}: {resp.status_code}")
                return False
        except Exception as e:
            print(f"✗ Login error: {e}")
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
    
    def test_books_performance(self):
        """Test that GET /api/books returns small response with cover URLs"""
        print("\n" + "="*70)
        print("TEST GROUP 1: Books API Performance")
        print("="*70)
        
        # Test 1.1: GET /api/books response size
        print("\n--- Test 1.1: GET /api/books response size ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/books")
            self.test(
                "GET /api/books returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                content_length = len(resp.content)
                # Should be around 35KB, definitely less than 100KB (was 24MB before)
                self.test(
                    "Response size is small (< 100KB)",
                    content_length < 100 * 1024,
                    f"Size: {content_length / 1024:.1f} KB (expected ~35KB)"
                )
                
                books = resp.json()
                self.test(
                    "Books list is array",
                    isinstance(books, list),
                    f"Count: {len(books)} books"
                )
                
                # Test 1.2: Check that covers are URLs, not base64
                if books:
                    books_with_covers = [b for b in books if b.get("cover")]
                    if books_with_covers:
                        sample_book = books_with_covers[0]
                        cover = sample_book.get("cover", "")
                        self.test_book_id = sample_book.get("id")
                        
                        # Cover should be a URL like /api/books/{id}/cover?v=...&s=thumb
                        is_url = cover.startswith("/api/books/") and "/cover" in cover
                        is_not_base64 = not cover.startswith("data:")
                        
                        self.test(
                            "Book covers are URLs (not base64)",
                            is_url and is_not_base64,
                            f"Sample cover: {cover[:80]}..."
                        )
                        
                        # Check URL format
                        has_version = "v=" in cover
                        has_size = "s=" in cover
                        self.test(
                            "Cover URL has version and size params",
                            has_version and has_size,
                            f"URL: {cover}"
                        )
                    else:
                        print("   ℹ No books with covers found in response")
                else:
                    print("   ℹ No books in database")
        except Exception as e:
            self.test("GET /api/books performance", False, f"Exception: {e}")
    
    def test_book_cover_endpoint(self):
        """Test book cover endpoint with caching headers"""
        print("\n" + "="*70)
        print("TEST GROUP 2: Book Cover Endpoint")
        print("="*70)
        
        if not self.test_book_id:
            print("   ℹ Skipping: No book with cover found")
            return
        
        # Test 2.1: GET /api/books/{id}/cover?v=...&s=thumb
        print(f"\n--- Test 2.1: GET /api/books/{self.test_book_id}/cover ---")
        try:
            # Get book details to find cover URL
            resp = self.admin_session.get(f"{BASE_URL}/books")
            books = resp.json()
            book = next((b for b in books if b.get("id") == self.test_book_id), None)
            
            if book and book.get("cover"):
                cover_url = book["cover"]
                # Make request to cover endpoint (public, no auth needed)
                cover_resp = requests.get(f"{BASE_URL.replace('/api', '')}{cover_url}")
                
                self.test(
                    "Cover endpoint returns 200",
                    cover_resp.status_code == 200,
                    f"Status: {cover_resp.status_code}"
                )
                
                if cover_resp.status_code == 200:
                    # Check content type
                    content_type = cover_resp.headers.get("Content-Type", "")
                    self.test(
                        "Cover is JPEG image",
                        "image/jpeg" in content_type,
                        f"Content-Type: {content_type}"
                    )
                    
                    # Check size (thumbnail should be ~20-30KB)
                    size = len(cover_resp.content)
                    self.test(
                        "Thumbnail size is reasonable (< 50KB)",
                        size < 50 * 1024,
                        f"Size: {size / 1024:.1f} KB"
                    )
                    
                    # Check caching headers
                    cache_control = cover_resp.headers.get("Cache-Control", "")
                    self.test(
                        "Has Cache-Control header with immutable",
                        "immutable" in cache_control and "max-age" in cache_control,
                        f"Cache-Control: {cache_control}"
                    )
                    
                    # Test 2.2: Full size cover (s=full)
                    print(f"\n--- Test 2.2: GET cover with s=full ---")
                    full_url = cover_url.replace("s=thumb", "s=full")
                    full_resp = requests.get(f"{BASE_URL.replace('/api', '')}{full_url}")
                    
                    self.test(
                        "Full size cover returns 200",
                        full_resp.status_code == 200,
                        f"Status: {full_resp.status_code}"
                    )
                    
                    if full_resp.status_code == 200:
                        full_size = len(full_resp.content)
                        self.test(
                            "Full size is larger than thumbnail",
                            full_size > size,
                            f"Full: {full_size / 1024:.1f} KB, Thumb: {size / 1024:.1f} KB"
                        )
        except Exception as e:
            self.test("Book cover endpoint", False, f"Exception: {e}")
    
    def test_gzip_compression(self):
        """Test that JSON API responses are gzip-compressed"""
        print("\n" + "="*70)
        print("TEST GROUP 3: GZip Compression")
        print("="*70)
        
        # Test 3.1: GET /api/members with gzip
        print("\n--- Test 3.1: GET /api/members with Accept-Encoding: gzip ---")
        try:
            headers = {"Accept-Encoding": "gzip"}
            resp = self.admin_session.get(f"{BASE_URL}/members", headers=headers)
            
            self.test(
                "Members endpoint returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                # Check if response is gzip-encoded
                content_encoding = resp.headers.get("Content-Encoding", "")
                self.test(
                    "Response is gzip-encoded",
                    "gzip" in content_encoding,
                    f"Content-Encoding: {content_encoding or '(none)'}"
                )
                
                # Verify data is still valid JSON
                try:
                    data = resp.json()
                    self.test(
                        "Gzipped response is valid JSON",
                        isinstance(data, list),
                        f"Type: {type(data)}, Count: {len(data)}"
                    )
                except:
                    self.test("Gzipped response is valid JSON", False, "Failed to parse JSON")
        except Exception as e:
            self.test("GZip compression", False, f"Exception: {e}")
        
        # Test 3.2: Verify backup.zip is NOT gzip-encoded
        print("\n--- Test 3.2: Verify /api/admin/backup.zip is NOT gzip-encoded ---")
        try:
            # Note: We won't actually download the full backup (can be large)
            # Just check the headers
            resp = self.admin_session.head(f"{BASE_URL}/admin/backup.zip")
            
            if resp.status_code == 200:
                content_encoding = resp.headers.get("Content-Encoding", "")
                self.test(
                    "Backup ZIP is NOT gzip-encoded",
                    "gzip" not in content_encoding,
                    f"Content-Encoding: {content_encoding or '(none)'}"
                )
                
                content_type = resp.headers.get("Content-Type", "")
                self.test(
                    "Backup has correct content type",
                    "application/zip" in content_type,
                    f"Content-Type: {content_type}"
                )
        except Exception as e:
            print(f"   ℹ Could not test backup.zip headers: {e}")
    
    def test_backup_endpoint(self):
        """Test that backup endpoint exists and returns correct format"""
        print("\n" + "="*70)
        print("TEST GROUP 4: Backup Endpoint")
        print("="*70)
        
        # Test 4.1: GET /api/admin/backup.zip exists
        print("\n--- Test 4.1: GET /api/admin/backup.zip endpoint ---")
        try:
            # Use HEAD to avoid downloading large file
            resp = self.admin_session.head(f"{BASE_URL}/admin/backup.zip")
            
            self.test(
                "Backup endpoint returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                # Check headers
                content_type = resp.headers.get("Content-Type", "")
                self.test(
                    "Backup is ZIP file",
                    "application/zip" in content_type,
                    f"Content-Type: {content_type}"
                )
                
                content_disp = resp.headers.get("Content-Disposition", "")
                self.test(
                    "Has Content-Disposition with filename",
                    "backup-perpustakaan-" in content_disp and ".zip" in content_disp,
                    f"Content-Disposition: {content_disp}"
                )
                
                # Check for X-Backup-Bytes header (used for integrity check)
                backup_bytes = resp.headers.get("X-Backup-Bytes")
                self.test(
                    "Has X-Backup-Bytes header for integrity check",
                    backup_bytes is not None,
                    f"X-Backup-Bytes: {backup_bytes}"
                )
        except Exception as e:
            self.test("Backup endpoint", False, f"Exception: {e}")
        
        # Test 4.2: Siswa cannot access backup
        print("\n--- Test 4.2: Siswa cannot access backup (403) ---")
        try:
            resp = self.siswa_session.head(f"{BASE_URL}/admin/backup.zip")
            self.test(
                "Siswa backup access returns 403",
                resp.status_code == 403,
                f"Status: {resp.status_code}"
            )
        except Exception as e:
            self.test("Siswa backup rejection", False, f"Exception: {e}")
        
        # Test 4.3: GET /api/admin/backup (JSON) still exists
        print("\n--- Test 4.3: GET /api/admin/backup (JSON fallback) ---")
        try:
            resp = self.admin_session.get(f"{BASE_URL}/admin/backup")
            self.test(
                "JSON backup endpoint returns 200",
                resp.status_code == 200,
                f"Status: {resp.status_code}"
            )
            
            if resp.status_code == 200:
                data = resp.json()
                required_fields = ["app", "version", "generated_at", "collections"]
                has_all = all(field in data for field in required_fields)
                self.test(
                    "JSON backup has required fields",
                    has_all,
                    f"Fields: {list(data.keys())}"
                )
        except Exception as e:
            self.test("JSON backup endpoint", False, f"Exception: {e}")
    
    def run_tests(self) -> bool:
        """Run all test groups"""
        print("\n" + "="*70)
        print("ITERATION 23 BACKEND TESTS: Performance & Backup Improvements")
        print("Testing: Books API size, Cover URLs, GZip, Backup endpoint")
        print("="*70)
        
        # Login
        if not self.login(self.admin_session, ADMIN_CREDS):
            return False
        if not self.login(self.siswa_session, SISWA_CREDS):
            return False
        
        # Run test groups
        self.test_books_performance()
        self.test_book_cover_endpoint()
        self.test_gzip_compression()
        self.test_backup_endpoint()
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"📊 Total: {self.tests_passed + self.tests_failed}")
        print("="*70)
        
        if self.tests_failed == 0:
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
