# Extra regression tests for loan leaderboard (iteration 3)
import os
import uuid

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def login(email, password, portal):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password, "portal": portal})
    assert r.status_code == 200, r.text
    s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s


@pytest.fixture(scope="module")
def admin():
    return login("admin@smansa.sch.id", "admin123", "admin")


class TestLoanLeaderboardExtra:
    def test_admin_access_and_shape(self, admin):
        r = admin.get(f"{BASE}/api/reports/loan-leaderboard")
        assert r.status_code == 200
        d = r.json()
        for k in ("month", "label", "total_loans", "active_students", "students", "classes", "months"):
            assert k in d
        assert d["total_loans"] == sum(s["loans"] for s in d["students"]) or len(d["students"]) == 10

    def test_seed_october_2026(self, admin):
        d = admin.get(f"{BASE}/api/reports/loan-leaderboard", params={"month": "2026-10"}).json()
        assert d["label"] == "Oktober 2026"
        assert d["total_loans"] >= 1

    def test_empty_month(self, admin):
        d = admin.get(f"{BASE}/api/reports/loan-leaderboard", params={"month": "2020-01"}).json()
        assert d["total_loans"] == 0 and d["students"] == [] and d["classes"] == []
        assert d["label"] == "Januari 2020"

    @pytest.mark.parametrize("bad", ["2026-1", "abc", "2026-00", "2026-13"])
    def test_bad_months(self, admin, bad):
        assert admin.get(f"{BASE}/api/reports/loan-leaderboard", params={"month": bad}).status_code == 400

    def test_unauth(self):
        assert requests.get(f"{BASE}/api/reports/loan-leaderboard").status_code in (401, 403)

    def test_export_bad_period_400(self, admin):
        r = admin.get(f"{BASE}/api/reports/export.pdf", params={"type": "peminjam", "period": "2026-13"})
        assert r.status_code == 400

    def test_export_empty_month_ok(self, admin):
        r = admin.get(f"{BASE}/api/reports/export.pdf", params={"type": "peminjam", "period": "2020-01"})
        assert r.status_code == 200 and r.content[:4] == b"%PDF"
        r = admin.get(f"{BASE}/api/reports/export.xlsx", params={"type": "peminjam", "period": "2020-01"})
        assert r.status_code == 200

    def test_export_portrait(self, admin):
        r = admin.get(f"{BASE}/api/reports/export.pdf", params={"type": "peminjam", "period": "2026-10"})
        assert r.status_code == 200 and "lanskap" not in r.headers.get("content-disposition", "")

    def test_visit_leaderboard_regression(self, admin):
        r = admin.get(f"{BASE}/api/reports/export.pdf", params={"type": "peringkat", "period": "2026-10"})
        assert r.status_code == 200 and r.content[:4] == b"%PDF"

    def test_returned_loans_still_count(self, admin):
        tag = uuid.uuid4().hex[:6]
        m = admin.post(f"{BASE}/api/members", json={"name": f"TEST_R_{tag}", "student_id": f"R{tag}", "class_name": f"TEST_RC_{tag}"}).json()["id"]
        b = admin.post(f"{BASE}/api/books", json={"title": f"TEST_R_{tag}", "author": "T", "shelf": "R-01"}).json()["id"]
        for act in ("pinjam", "kembali", "pinjam"):
            r = admin.post(f"{BASE}/api/transactions", json={"member_id": m, "book_id": b, "action": act})
            assert r.status_code == 200, r.text
        d = admin.get(f"{BASE}/api/reports/loan-leaderboard").json()
        me = next(s for s in d["students"] if s["member_id"] == m)
        assert me["loans"] == 2 and me["titles"] == 1
