"""Peringkat rajin meminjam: siswa & kelas dengan peminjaman buku terbanyak dalam satu bulan (WIB)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from reports_pdf import WIB

MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
_db = None


def _wib_month(value) -> str:
    """Kunci bulan (YYYY-MM) zona WIB dari tanggal transaksi (ISO UTC)."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.strftime("%Y-%m")
        return dt.astimezone(WIB).strftime("%Y-%m")
    except ValueError:
        return str(value)[:7]


def _wib_day(value) -> str:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (dt.astimezone(WIB) if dt.tzinfo else dt).date().isoformat()
    except ValueError:
        return str(value)[:10]


async def loan_leaderboard(month: Optional[str] = None, limit: int = 10):
    now = datetime.now(WIB)
    if month:
        try:
            y, m = (int(x) for x in month.split("-"))
            if not 1 <= m <= 12:
                raise ValueError
        except ValueError:
            raise HTTPException(400, "Format bulan harus YYYY-MM")
    else:
        y, m = now.year, now.month
    key = f"{y:04d}-{m:02d}"
    all_loans = await _db.transactions.find({"action": "pinjam"}, {"_id": 0, "member_id": 1, "member_name": 1, "class_name": 1, "book_id": 1, "book_title": 1, "date": 1}).to_list(200000)
    rows = [t for t in all_loans if _wib_month(t.get("date")) == key]
    ids = list({t["member_id"] for t in rows if t.get("member_id")})
    members = {x["id"]: x for x in await _db.members.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "name": 1, "class_name": 1, "photo": 1}).to_list(None)} if ids else {}

    students, classes = {}, {}
    for t in rows:
        mid = t.get("member_id") or t.get("member_name")
        mem = members.get(t.get("member_id")) or {}
        cls_name = (t.get("class_name") or mem.get("class_name") or "").strip()
        st = students.setdefault(mid, {"member_id": t.get("member_id"), "name": t.get("member_name", "-"), "class_name": cls_name or "-", "loans": 0, "books": set(), "days": set()})
        st["loans"] += 1
        st["books"].add(t.get("book_title") or t.get("book_id"))
        st["days"].add(_wib_day(t.get("date")))
        c = classes.setdefault(cls_name or "Tanpa kelas", {"class_name": cls_name or "Tanpa kelas", "loans": 0, "members": set()})
        c["loans"] += 1
        c["members"].add(mid)

    total = len(rows)
    ranked = sorted(students.values(), key=lambda x: (-x["loans"], -len(x["books"]), -len(x["days"]), x["name"]))
    out_students = []
    for i, st in enumerate(ranked[:limit], 1):
        mem = members.get(st["member_id"]) or {}
        out_students.append({
            "rank": i, "member_id": st["member_id"], "name": mem.get("name") or st["name"],
            "class_name": mem.get("class_name") or st["class_name"], "photo": mem.get("photo", ""),
            "loans": st["loans"], "books": len(st["books"]), "days": len(st["days"]),
            "pct": round(st["loans"] * 100 / total, 1) if total else 0.0,
        })
    out_classes = [{"rank": i, "class_name": c["class_name"], "loans": c["loans"], "members": len(c["members"]), "pct": round(c["loans"] * 100 / total, 1) if total else 0.0}
                   for i, c in enumerate(sorted(classes.values(), key=lambda x: (-x["loans"], -len(x["members"]), x["class_name"])), 1)]
    months = sorted({k for k in (_wib_month(t.get("date")) for t in all_loans) if k} | {now.strftime("%Y-%m")}, reverse=True)
    return {"month": key, "label": f"{MONTHS_ID[m - 1]} {y}", "total_loans": total, "active_students": len(students),
            "students": out_students, "classes": out_classes, "months": months}


def build_router(db, current_user):
    global _db
    _db = db
    r = APIRouter()

    @r.get("/loans/leaderboard")
    async def leaderboard(month: Optional[str] = None, user=Depends(current_user)):
        return await loan_leaderboard(month)

    return r
