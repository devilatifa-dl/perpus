from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from reports_pdf import WIB, build_loans

MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def wib_day(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return dt.astimezone(WIB).date() if dt.tzinfo else dt.date()


def bucket(d, group):
    return d.strftime("%Y-%m") if group == "month" else d.isoformat()


def bucket_label(key, group):
    if group == "month":
        y, m = key.split("-")
        return f"{MONTHS[int(m) - 1]} {y}"
    d = date.fromisoformat(key)
    return f"{d.day} {MONTHS[d.month - 1]}"


def series_keys(d1, d2, group):
    keys, cur = [], d1
    while cur <= d2:
        k = bucket(cur, group)
        if not keys or keys[-1] != k:
            keys.append(k)
        cur += timedelta(days=1)
    return keys


def build_router(db, current_user, staff_only, overdue_loans, visits_auto_close):
    r = APIRouter()

    @r.get("/reports/summary")
    async def report_summary(start: str = "", end: str = "", group: str = "day", user=Depends(current_user)):
        staff_only(user)
        if group not in ("day", "month"):
            raise HTTPException(400, "Pengelompokan tidak valid")
        today = datetime.now(WIB).date()
        try:
            d1 = date.fromisoformat(start) if start else today - timedelta(days=29)
            d2 = date.fromisoformat(end) if end else today
        except ValueError:
            raise HTTPException(400, "Format tanggal tidak valid")
        if d1 > d2:
            d1, d2 = d2, d1
        if (d2 - d1).days > 3 * 366:
            raise HTTPException(400, "Rentang tanggal maksimal 3 tahun")
        await visits_auto_close()

        loans = build_loans(await db.transactions.find({}, {"_id": 0}).to_list(100000))
        visits = await db.visits.find({"date": {"$gte": d1.isoformat(), "$lte": d2.isoformat()}}, {"_id": 0, "photo": 0}).to_list(100000)
        keys = series_keys(d1, d2, group)
        series = {k: {"key": k, "label": bucket_label(k, group), "loans": 0, "returns": 0, "visits": 0} for k in keys}
        books, members = {}, {}

        def member_row(mid, name, cls):
            return members.setdefault(mid, {"member_id": mid, "name": name, "class_name": cls or "", "loans": 0, "visits": 0})

        for l in loans:
            bd = wib_day(l.get("borrowed_at"))
            if bd and d1 <= bd <= d2:
                series[bucket(bd, group)]["loans"] += 1
                b = books.setdefault(l["book_id"], {"book_id": l["book_id"], "title": l.get("book_title", ""), "count": 0})
                b["count"] += 1
                member_row(l["member_id"], l.get("member_name", ""), "")["loans"] += 1
            rd = wib_day(l.get("returned_at"))
            if rd and d1 <= rd <= d2:
                series[bucket(rd, group)]["returns"] += 1
        for v in visits:
            k = bucket(date.fromisoformat(v["date"]), group)
            if k in series:
                series[k]["visits"] += 1
            if v.get("kind") == "anggota" and v.get("member_id"):
                m = member_row(v["member_id"], v.get("name", ""), v.get("class_name", ""))
                m["visits"] += 1
                m["class_name"] = m["class_name"] or v.get("class_name", "")

        info = {m["id"]: m for m in await db.members.find({"id": {"$in": list(members)}}, {"_id": 0, "id": 1, "name": 1, "class_name": 1}).to_list(10000)}
        for mid, m in members.items():
            if mid in info:
                m["name"], m["class_name"] = info[mid]["name"], info[mid].get("class_name", "")
            m["score"] = m["loans"] + m["visits"]

        agg = await db.books.aggregate([{"$group": {"_id": None, "stock": {"$sum": "$stock"}, "titles": {"$sum": 1}}}]).to_list(1)
        a = agg[0] if agg else {"stock": 0, "titles": 0}
        kpis = {
            "books": a["stock"], "titles": a["titles"],
            "members": await db.members.count_documents({}),
            "active_loans": sum(1 for l in loans if l["status"] == "Dipinjam"),
            "overdue": len(await overdue_loans()),
            "visits_today": await db.visits.count_documents({"date": today.isoformat()}),
        }
        rows = list(series.values())
        return {
            "start": d1.isoformat(), "end": d2.isoformat(), "group": group, "kpis": kpis,
            "totals": {"loans": sum(x["loans"] for x in rows), "returns": sum(x["returns"] for x in rows), "visits": sum(x["visits"] for x in rows)},
            "series": rows,
            "top_books": sorted(books.values(), key=lambda b: -b["count"])[:10],
            "top_members": sorted(members.values(), key=lambda m: (-m["score"], -m["loans"]))[:10],
        }

    return r
