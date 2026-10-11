import os
import uuid

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://perpus-sekolah-4.preview.emergentagent.com").rstrip("/")


@pytest.fixture
def client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123"})
    assert response.status_code == 200, response.text
    return session


def test_auth_cookie_me_and_logout():
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@smansa.sch.id", "password": "admin123"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert "access_token" in session.cookies
    assert session.cookies.get_dict()["access_token"]
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
    response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200 and response.json()["role"] == role


def test_invalid_login_returns_401():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@smansa.sch.id", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"]


def test_catalog_and_shelves(client):
    for path, key in [("books", "title"), ("members", "name"), ("shelves", "id"), ("transactions", "id")]:
        response = client.get(f"{BASE_URL}/api/{path}")
        assert response.status_code == 200 and isinstance(response.json(), list)
        assert response.json() and key in response.json()[0]


def test_book_create_delete_and_siswa_forbidden(client):
    title = f"TEST_{uuid.uuid4().hex[:8]}"
    created = client.post(f"{BASE_URL}/api/books", json={"title": title, "author": "Tester", "category": "Umum", "shelf": "R-01"})
    assert created.status_code == 200 and created.json()["title"] == title
    book_id = created.json()["id"]
    assert any(book["id"] == book_id for book in client.get(f"{BASE_URL}/api/books").json())
    assert client.delete(f"{BASE_URL}/api/books/{book_id}").status_code == 200
    siswa = requests.Session()
    assert siswa.post(f"{BASE_URL}/api/auth/login", json={"email": "siswa@smansa.sch.id", "password": "siswa123"}).status_code == 200
    assert siswa.post(f"{BASE_URL}/api/books", json={"title": "TEST_forbidden", "author": "Tester"}).status_code == 403


def test_member_create_persists(client):
    payload = {"name": f"TEST_{uuid.uuid4().hex[:8]}", "student_id": uuid.uuid4().hex[:8], "class_name": "X TEST"}
    response = client.post(f"{BASE_URL}/api/members", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == payload["name"]
    assert any(member["id"] == response.json()["id"] for member in client.get(f"{BASE_URL}/api/members").json())


def test_transaction_rejects_missing_entities(client):
    response = client.post(f"{BASE_URL}/api/transactions", json={"member_id": "missing", "book_id": "missing", "action": "pinjam"})
    assert response.status_code == 404


def test_reports_and_dashboard(client):
    dashboard = client.get(f"{BASE_URL}/api/dashboard")
    assert dashboard.status_code == 200 and dashboard.json()["books"] >= 1
    reports = client.get(f"{BASE_URL}/api/reports")
    assert reports.status_code == 200
    assert all(key in reports.json() for key in ("transactions", "incoming", "missing"))