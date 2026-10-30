import os
import uuid

import pytest
import requests


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


# ---- Fixtures ----
@pytest.fixture
def client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123"})
    assert response.status_code == 200, response.text
    return session


@pytest.fixture
def siswa_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json={"email": "siswa@smansa.sch.id", "password": "siswa123", "portal": "siswa"})
    assert response.status_code == 200
    return session


# ---- Auth ----
def test_auth_cookie_me_and_logout():
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert "access_token" in session.cookies
    assert "HttpOnly" in response.headers.get("set-cookie", "")
    me = session.get(f"{BASE_URL}/api/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "admin@smansa.sch.id"
    assert session.post(f"{BASE_URL}/api/auth/logout").status_code == 200
    assert session.get(f"{BASE_URL}/api/auth/me").status_code == 401


@pytest.mark.parametrize("email,password,role", [
    ("admin@smansa.sch.id", "admin123", "admin"),
    ("petugas@smansa.sch.id", "petugas123", "petugas"),
    ("siswa@smansa.sch.id", "siswa123", "siswa"),
])
def test_all_demo_roles(email, password, role):
    portal = "siswa" if role == "siswa" else "admin"
    response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password, "portal": portal})
    assert response.status_code == 200 and response.json()["role"] == role


def test_invalid_login_returns_401():
    # Use a unique non-existing identifier to avoid lockout on real accounts.
    bogus = f"nope-{uuid.uuid4().hex[:6]}@smansa.sch.id"
    response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": bogus, "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"]


# ---- Catalog ----
def test_catalog_and_shelves(client):
    for path, key in [("books", "title"), ("members", "name"), ("shelves", "id"), ("transactions", "id")]:
        response = client.get(f"{BASE_URL}/api/{path}")
        assert response.status_code == 200 and isinstance(response.json(), list)
        assert response.json() and key in response.json()[0]


def test_books_have_cover_field(client):
    books = client.get(f"{BASE_URL}/api/books").json()
    assert books
    for b in books:
        assert "cover" in b, f"Book missing 'cover' field: {b.get('id')}"


def test_members_have_photo_field(client):
    members = client.get(f"{BASE_URL}/api/members").json()
    assert members
    for m in members:
        assert "photo" in m, f"Member missing 'photo' field: {m.get('id')}"


def test_shelves_have_capacity(client):
    shelves = client.get(f"{BASE_URL}/api/shelves").json()
    ids = {s["id"] for s in shelves}
    assert {"R-01", "R-02", "R-03"}.issubset(ids)
    for s in shelves:
        assert isinstance(s.get("capacity"), int)


# ---- Book CRUD with cover ----
def test_book_create_with_cover_and_delete(client):
    title = f"TEST_{uuid.uuid4().hex[:8]}"
    cover_url = "https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=400&q=70"
    created = client.post(f"{BASE_URL}/api/books", json={"title": title, "author": "Tester", "category": "Umum", "shelf": "R-01", "cover": cover_url})
    assert created.status_code == 200
    data = created.json()
    assert data["title"] == title
    assert data["cover"] == cover_url
    book_id = data["id"]
    fetched = next((b for b in client.get(f"{BASE_URL}/api/books").json() if b["id"] == book_id), None)
    assert fetched and fetched["cover"] == cover_url
    assert client.delete(f"{BASE_URL}/api/books/{book_id}").status_code == 200
    assert all(b["id"] != book_id for b in client.get(f"{BASE_URL}/api/books").json())


def test_siswa_forbidden_from_mutations(siswa_client):
    assert siswa_client.post(f"{BASE_URL}/api/books", json={"title": "TEST_forbid", "author": "x"}).status_code == 403
    assert siswa_client.post(f"{BASE_URL}/api/members", json={"name": "TEST_forbid", "student_id": "x", "class_name": "X"}).status_code == 403
    assert siswa_client.delete(f"{BASE_URL}/api/books/BK-1042").status_code == 403


def test_delete_nonexistent_book_returns_404(client):
    assert client.delete(f"{BASE_URL}/api/books/BK-DOESNOTEXIST").status_code == 404


# ---- Member creation with photo ----
def test_member_create_with_photo_persists(client):
    photo_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    payload = {"name": f"TEST_{uuid.uuid4().hex[:8]}", "student_id": uuid.uuid4().hex[:8], "class_name": "X TEST", "photo": photo_b64}
    response = client.post(f"{BASE_URL}/api/members", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["photo"] == photo_b64
    members = client.get(f"{BASE_URL}/api/members").json()
    fetched = next((m for m in members if m["id"] == data["id"]), None)
    assert fetched and fetched["photo"] == photo_b64


# ---- Transactions borrow/return state transitions ----
def _available_book_id(client):
    books = client.get(f"{BASE_URL}/api/books").json()
    for b in books:
        if b["status"] == "Tersedia":
            return b["id"]
    pytest.skip("No available books to borrow")


def test_transaction_pinjam_kembali_state_transitions(client):
    member_id = client.post(f"{BASE_URL}/api/members", json={"name": "TEST_Loan", "student_id": uuid.uuid4().hex[:6], "class_name": "X"}).json()["id"]
    book_id = client.post(f"{BASE_URL}/api/books", json={"title": f"TEST_LOAN_{uuid.uuid4().hex[:6]}", "author": "T", "shelf": "R-01"}).json()["id"]

    before = next(b for b in client.get(f"{BASE_URL}/api/books").json() if b["id"] == book_id)["available"]
    # pinjam -> available stock -1
    r = client.post(f"{BASE_URL}/api/transactions", json={"member_id": member_id, "book_id": book_id, "action": "pinjam"})
    assert r.status_code == 200 and r.json()["action"] == "pinjam"
    book = next(b for b in client.get(f"{BASE_URL}/api/books").json() if b["id"] == book_id)
    assert book["available"] == before - 1

    # same member borrowing the same title again -> 400
    r2 = client.post(f"{BASE_URL}/api/transactions", json={"member_id": member_id, "book_id": book_id, "action": "pinjam"})
    assert r2.status_code == 400

    # kembali -> available stock restored
    r3 = client.post(f"{BASE_URL}/api/transactions", json={"member_id": member_id, "book_id": book_id, "action": "kembali"})
    assert r3.status_code == 200 and r3.json()["action"] == "kembali"
    book = next(b for b in client.get(f"{BASE_URL}/api/books").json() if b["id"] == book_id)
    assert book["available"] == before and book["status"] == "Tersedia"
    client.delete(f"{BASE_URL}/api/books/{book_id}")
    client.delete(f"{BASE_URL}/api/members/{member_id}")


def test_transaction_rejects_missing_entities(client):
    response = client.post(f"{BASE_URL}/api/transactions", json={"member_id": "missing", "book_id": "missing", "action": "pinjam"})
    assert response.status_code == 404


# ---- Reports & dashboard ----
def test_reports_structure(client):
    reports = client.get(f"{BASE_URL}/api/reports")
    assert reports.status_code == 200
    data = reports.json()
    for key in ("transactions", "incoming", "missing"):
        assert key in data and isinstance(data[key], list)


def test_dashboard_counts(client):
    dashboard = client.get(f"{BASE_URL}/api/dashboard")
    assert dashboard.status_code == 200
    data = dashboard.json()
    for key in ("books", "members", "borrowed", "missing", "incoming", "transactions"):
        assert key in data and isinstance(data[key], int)
    assert data["books"] >= 1


# ---- Auth protection ----
def test_endpoints_require_auth():
    for path in ["/api/auth/me", "/api/books", "/api/members", "/api/shelves", "/api/transactions", "/api/reports", "/api/dashboard"]:
        r = requests.get(f"{BASE_URL}{path}")
        assert r.status_code == 401, f"{path} should require auth, got {r.status_code}"
