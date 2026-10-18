"""Fitur pengunjung perpustakaan: scan QR masuk/keluar, tamu, auto-keluar jam sekolah, statistik."""
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from reports_pdf import WIB

DEFAULT_CHECKOUT = "14:00"
STAT_PERIODS = ("harian", "7hari", "30hari", "bulanan", "semua")
_db = None


class ScanInput(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)


class GuestInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    purpose: str = Field("", max_length=120)
    origin: str = Field("", max_length=80)


class VisitConfigInput(BaseModel):
    checkout_time: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


def _parse(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB)


def in_visit_period(value, period, now):
    dt = _parse(value)
    if dt is None or period == "semua":
        return True
    if period == "harian":
        return dt.date() == now.date()
    if period == "bulanan":
        return (dt.year, dt.month) == (now.year, now.month)
    if period in ("7hari", "30hari"):
        days = 7 if period == "7hari" else 30
        return dt.date() >= (now.date() - timedelta(days=days - 1))
    return True


async def checkout_time():
    doc = await _db.settings.find_one({"id": "main"}, {"_id": 0, "visit_checkout_time": 1}) or {}
    value = doc.get("visit_checkout_time") or DEFAULT_CHECKOUT
    h, m = value.split(":")
    return int(h), int(m), value


def _duration(cin, cout):
    a, b = _parse(cin), _parse(cout)
    if not a or not b:
        return None
    return max(int((b - a).total_seconds() // 60), 0)


async def visits_auto_close():
    """Pengunjung yang belum scan keluar otomatis tercatat keluar pada jam sekolah (WIB)."""
    h, m, _ = await checkout_time()
    now = datetime.now(WIB)
    rows = await _db.visits.find({"check_out": None}, {"_id": 0, "id": 1, "check_in": 1}).to_list(10000)
    for v in rows:
        cin = _parse(v.get("check_in"))
        if not cin:
            continue
        cutoff = cin.replace(hour=h, minute=m, second=0, microsecond=0)
        if cin >= cutoff:  # masuk setelah jam pulang → ditutup di akhir hari itu
            cutoff = cin.replace(hour=23, minute=59, second=0, microsecond=0)
        if now >= cutoff:
            out = cutoff.astimezone(timezone.utc).isoformat()
            await _db.visits.update_one({"id": v["id"], "check_out": None}, {"$set": {"check_out": out, "checkout_type": "otomatis", "duration_min": _duration(v["check_in"], out)}})


def _clean(doc):
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


async def visit_stats(period: str = "7hari"):
    if period not in STAT_PERIODS:
        raise HTTPException(400, "Periode tidak valid")
    now = datetime.now(WIB)
    q = {}
    bounds = {"harian": 0, "7hari": 6, "30hari": 29}
    if period in bounds or period == "bulanan":
        start_day = now.date().replace(day=1) if period == "bulanan" else now.date() - timedelta(days=bounds[period])
        start_dt = datetime(start_day.year, start_day.month, start_day.day, tzinfo=WIB) - timedelta(days=1)  # longgar 1 hari, disaring tepat di bawah
        q = {"check_in": {"$gte": start_dt.astimezone(timezone.utc).isoformat()}}
    proj = {"_id": 0, "photo": 0}
    rows = [r for r in await _db.visits.find(q, proj).sort("check_in", -1).limit(50000).to_list(50000) if in_visit_period(r.get("check_in"), period, now)]
    total = len(rows)
    pct = lambda n: round(n * 100 / total, 1) if total else 0.0

    # rentang hari
    if period == "harian":
        start = now.date()
    elif period == "7hari":
        start = now.date() - timedelta(days=6)
    elif period == "30hari":
        start = now.date() - timedelta(days=29)
    elif period == "bulanan":
        start = now.date().replace(day=1)
    else:
        dates = [_parse(r.get("check_in")).date() for r in rows if _parse(r.get("check_in"))]
        start = max(min(dates), now.date() - timedelta(days=59)) if dates else now.date() - timedelta(days=6)
    per_day_map = {}
    d = start
    while d <= now.date():
        per_day_map[d.isoformat()] = {"date": d.isoformat(), "total": 0, "anggota": 0, "tamu": 0}
        d += timedelta(days=1)
    per_class, per_hour, types = {}, {}, {"scan": 0, "manual": 0, "otomatis": 0}
    members, durations, inside = set(), [], 0
    for r in rows:
        dt = _parse(r.get("check_in"))
        key = dt.date().isoformat() if dt else None
        if key in per_day_map:
            per_day_map[key]["total"] += 1
            per_day_map[key]["anggota" if r.get("kind") == "anggota" else "tamu"] += 1
        cls = (r.get("class_name") or "").strip() or ("Tamu" if r.get("kind") == "tamu" else "Tanpa kelas")
        if r.get("kind") == "tamu":
            cls = "Tamu"
        per_class[cls] = per_class.get(cls, 0) + 1
        if dt:
            per_hour[dt.hour] = per_hour.get(dt.hour, 0) + 1
        if r.get("member_id"):
            members.add(r["member_id"])
        if r.get("check_out"):
            types[r.get("checkout_type") or "manual"] = types.get(r.get("checkout_type") or "manual", 0) + 1
            dur = r.get("duration_min")
            if dur is None:
                dur = _duration(r.get("check_in"), r.get("check_out"))
            if dur is not None:
                durations.append(dur)
        else:
            inside += 1
    per_day = list(per_day_map.values())
    anggota = sum(1 for r in rows if r.get("kind") == "anggota")
    tamu = total - anggota
    closed = sum(types.values())
    peak = max(per_day, key=lambda x: x["total"]) if per_day and total else None
    peak_hour = max(per_hour.items(), key=lambda x: x[1])[0] if per_hour else None
    return {
        "period": period,
        "total": total,
        "days": len(per_day),
        "avg_per_day": round(total / len(per_day), 1) if per_day else 0,
        "unique_members": len(members),
        "inside": inside,
        "avg_duration_min": round(sum(durations) / len(durations)) if durations else 0,
        "kinds": [{"label": "Anggota", "count": anggota, "pct": pct(anggota)}, {"label": "Tamu", "count": tamu, "pct": pct(tamu)}],
        "per_day": per_day,
        "per_class": sorted([{"class_name": k, "count": v, "pct": pct(v)} for k, v in per_class.items()], key=lambda x: (-x["count"], x["class_name"])),
        "per_hour": [{"hour": h, "count": per_hour.get(h, 0)} for h in range(6, 18)],
        "checkout_types": [{"label": {"scan": "Scan keluar", "manual": "Dicatat petugas", "otomatis": "Otomatis jam sekolah"}.get(k, k), "key": k, "count": v, "pct": round(v * 100 / closed, 1) if closed else 0.0} for k, v in types.items()],
        "peak_day": peak,
        "peak_hour": peak_hour,
        "generated_at": now.isoformat(),
    }


MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


async def visit_leaderboard(month: Optional[str] = None, limit: int = 10):
    """Peringkat siswa & kelas dengan kunjungan terbanyak dalam satu bulan (WIB)."""
    now = datetime.now(WIB)
    if month:
        try:
            y, m = (int(x) for x in month.split("-"))
            if not 1 <= m <= 12: raise ValueError
        except ValueError:
            raise HTTPException(400, "Format bulan harus YYYY-MM")
    else:
        y, m = now.year, now.month
    key = f"{y:04d}-{m:02d}"
    rows = [r for r in await _db.visits.find({"kind": "anggota", "date": {"$regex": f"^{key}"}}, {"_id": 0, "photo": 0}).limit(50000).to_list(50000)]
    students, classes = {}, {}
    for r in rows:
        mid = r.get("member_id") or r.get("name")
        st = students.setdefault(mid, {"member_id": r.get("member_id"), "name": r.get("name", "-"), "class_name": r.get("class_name") or "-", "visits": 0, "days": set(), "minutes": 0})
        st["visits"] += 1; st["days"].add(r.get("date")); st["minutes"] += int(r.get("duration_min") or 0)
        cls = (r.get("class_name") or "").strip() or "Tanpa kelas"
        c = classes.setdefault(cls, {"class_name": cls, "visits": 0, "members": set()})
        c["visits"] += 1; c["members"].add(mid)
    members = {m_["id"]: m_ for m_ in await _db.members.find({"id": {"$in": [k for k in students if k]}}, {"_id": 0, "id": 1, "name": 1, "class_name": 1, "photo": 1}).to_list(None)}
    total = len(rows)
    ranked = sorted(students.values(), key=lambda x: (-x["visits"], -len(x["days"]), -x["minutes"], x["name"]))
    out_students = []
    for i, st in enumerate(ranked[:limit], 1):
        mem = members.get(st["member_id"]) or {}
        out_students.append({"rank": i, "member_id": st["member_id"], "name": mem.get("name") or st["name"], "class_name": mem.get("class_name") or st["class_name"], "photo": mem.get("photo", ""), "visits": st["visits"], "days": len(st["days"]), "minutes": st["minutes"], "pct": round(st["visits"] * 100 / total, 1) if total else 0.0})
    out_classes = [{"rank": i, "class_name": c["class_name"], "visits": c["visits"], "members": len(c["members"]), "pct": round(c["visits"] * 100 / total, 1) if total else 0.0}
                   for i, c in enumerate(sorted(classes.values(), key=lambda x: (-x["visits"], -len(x["members"]), x["class_name"])), 1)]
    months = sorted({(v.get("date") or "")[:7] for v in await _db.visits.find({"kind": "anggota"}, {"_id": 0, "date": 1}).to_list(50000) if v.get("date")} | {now.strftime("%Y-%m")}, reverse=True)
    return {"month": key, "label": f"{MONTHS_ID[m - 1]} {y}", "total_visits": total, "active_students": len(students), "students": out_students, "classes": out_classes, "months": months}


def build_router(db, current_user, staff_only, now_iso):
    global _db
    _db = db
    r = APIRouter()

    def new_id():
        return "VS-" + str(uuid.uuid4())[:8].upper()

    def today_wib():
        return datetime.now(WIB).date().isoformat()

    async def find_member(code: str):
        c = code.strip()
        m = await db.members.find_one({"id": {"$regex": f"^{re.escape(c)}$", "$options": "i"}}, {"_id": 0})
        if not m:
            m = await db.members.find_one({"student_id": c}, {"_id": 0})
        return m

    @r.get("/visits")
    async def list_visits(date: Optional[str] = None, user=Depends(current_user)):
        staff_only(user)
        await visits_auto_close()
        day = date or today_wib()
        rows = [v for v in await db.visits.find({"date": day}, {"_id": 0}).sort("check_in", -1).to_list(5000)]
        _, _, ct = await checkout_time()
        return {
            "date": day,
            "checkout_time": ct,
            "items": rows,
            "summary": {
                "total": len(rows),
                "inside": sum(1 for v in rows if not v.get("check_out")),
                "anggota": sum(1 for v in rows if v.get("kind") == "anggota"),
                "tamu": sum(1 for v in rows if v.get("kind") == "tamu"),
            },
        }

    @r.get("/visits/member-search")
    async def member_search(q: str = "", user=Depends(current_user)):
        """Cari anggota berdasarkan nama / NIS / kode kartu / kelas untuk dicatat kunjungannya."""
        staff_only(user)
        q = (q or "").strip()
        if len(q) < 2:
            return []
        await visits_auto_close()
        rx = {"$regex": re.escape(q), "$options": "i"}
        rows = await db.members.find(
            {"$or": [{"name": rx}, {"student_id": rx}, {"id": rx}, {"class_name": rx}]},
            {"_id": 0, "id": 1, "name": 1, "class_name": 1, "student_id": 1, "photo": 1},
        ).limit(40).to_list(40)
        ql = q.lower()
        rows.sort(key=lambda m: (not (m.get("name", "").lower().startswith(ql)), m.get("name", "").lower()))
        rows = rows[:8]
        ids = [m["id"] for m in rows]
        inside = {v["member_id"] for v in await db.visits.find({"member_id": {"$in": ids}, "check_out": None}, {"_id": 0, "member_id": 1}).to_list(100)}
        for m in rows:
            m["inside"] = m["id"] in inside
        return rows

    @r.post("/visits/scan")
    async def scan_visit(data: ScanInput, user=Depends(current_user)):
        staff_only(user)
        await visits_auto_close()
        member = await find_member(data.code)
        if not member:
            raise HTTPException(404, "Kode kartu anggota tidak dikenal")
        now = datetime.now(timezone.utc)
        open_visit = await db.visits.find_one({"member_id": member["id"], "check_out": None}, {"_id": 0}, sort=[("check_in", -1)])
        if open_visit:
            cin = _parse(open_visit["check_in"])
            if cin and (now - cin).total_seconds() < 30:
                return {"action": "sudah_masuk", "visit": open_visit, "member": member}
            out = now.isoformat()
            await db.visits.update_one({"id": open_visit["id"]}, {"$set": {"check_out": out, "checkout_type": "scan", "duration_min": _duration(open_visit["check_in"], out), "checkout_by": user["name"]}})
            return {"action": "keluar", "visit": await db.visits.find_one({"id": open_visit["id"]}, {"_id": 0}), "member": member}
        last = await db.visits.find_one({"member_id": member["id"]}, {"_id": 0}, sort=[("check_out", -1)])
        if last and last.get("checkout_type") == "scan" and last.get("check_out"):
            lo = _parse(last["check_out"])
            if lo and (now - lo).total_seconds() < 30:
                return {"action": "sudah_keluar", "visit": last, "member": member}
        doc = {"id": new_id(), "kind": "anggota", "member_id": member["id"], "student_id": member.get("student_id", ""), "name": member["name"], "class_name": member.get("class_name", ""), "purpose": "", "origin": "", "photo": member.get("photo", ""), "check_in": now.isoformat(), "check_out": None, "checkout_type": None, "duration_min": None, "date": today_wib(), "recorded_by": user["name"]}
        await db.visits.insert_one(doc)
        return {"action": "masuk", "visit": _clean(doc), "member": member}

    @r.post("/visits/guest")
    async def guest_visit(data: GuestInput, user=Depends(current_user)):
        staff_only(user)
        doc = {"id": new_id(), "kind": "tamu", "member_id": None, "student_id": "", "name": data.name.strip(), "class_name": "Tamu", "purpose": data.purpose.strip(), "origin": data.origin.strip(), "photo": "", "check_in": now_iso(), "check_out": None, "checkout_type": None, "duration_min": None, "date": today_wib(), "recorded_by": user["name"]}
        await db.visits.insert_one(doc)
        return _clean(doc)

    @r.post("/visits/{visit_id}/checkout")
    async def checkout_visit(visit_id: str, user=Depends(current_user)):
        staff_only(user)
        v = await db.visits.find_one({"id": visit_id}, {"_id": 0})
        if not v:
            raise HTTPException(404, "Data pengunjung tidak ditemukan")
        if v.get("check_out"):
            raise HTTPException(400, "Pengunjung sudah tercatat keluar")
        out = now_iso()
        await db.visits.update_one({"id": visit_id}, {"$set": {"check_out": out, "checkout_type": "manual", "duration_min": _duration(v["check_in"], out), "checkout_by": user["name"]}})
        return await db.visits.find_one({"id": visit_id}, {"_id": 0})

    @r.delete("/visits/{visit_id}")
    async def delete_visit(visit_id: str, user=Depends(current_user)):
        staff_only(user)
        res = await db.visits.delete_one({"id": visit_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Data pengunjung tidak ditemukan")
        return {"ok": True}

    @r.get("/visits/config")
    async def get_config(user=Depends(current_user)):
        staff_only(user)
        _, _, ct = await checkout_time()
        return {"checkout_time": ct}

    @r.put("/visits/config")
    async def put_config(data: VisitConfigInput, user=Depends(current_user)):
        staff_only(user)
        await db.settings.update_one({"id": "main"}, {"$set": {"visit_checkout_time": data.checkout_time}}, upsert=True)
        await visits_auto_close()
        return {"checkout_time": data.checkout_time}

    @r.get("/visits/history")
    async def history(period: str = "semua", user=Depends(current_user)):
        staff_only(user)
        if period not in STAT_PERIODS:
            raise HTTPException(400, "Periode tidak valid")
        await visits_auto_close()
        now = datetime.now(WIB)
        rows = await db.visits.find({}, {"_id": 0, "photo": 0}).sort("check_in", -1).to_list(20000)
        return [v for v in rows if in_visit_period(v.get("check_in"), period, now)]

    @r.get("/visits/leaderboard")
    async def leaderboard(month: Optional[str] = None, user=Depends(current_user)):
        await visits_auto_close()
        data = await visit_leaderboard(month)
        if user.get("role") == "siswa":
            for st in data["students"]:
                st.pop("minutes", None)
        return data

    @r.get("/visits/stats")
    async def stats(period: str = "7hari", user=Depends(current_user)):
        staff_only(user)
        await visits_auto_close()
        return await visit_stats(period)

    return r
