import base64, io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ASSETS = Path(__file__).parent / "assets"
WIB = timezone(timedelta(hours=7))
NAVY = colors.HexColor("#0f2745")
BLUE = colors.HexColor("#0284c7")
LIGHT = colors.HexColor("#f1f5f9")

TITLES = {"transaksi": "Laporan Transaksi Peminjaman", "masuk": "Laporan Buku Masuk", "hilang": "Laporan Buku Hilang"}
PERIODS = {"semua": "Semua waktu", "harian": "Harian", "bulanan": "Bulanan"}


BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
BULAN_PANJANG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def fmt_long(dt, with_time=False):
    base = f"{dt.day} {BULAN_PANJANG[dt.month - 1]} {dt.year}"
    return f"{base}, {dt.strftime('%H:%M')}" if with_time else base


def fmt_date(value, with_time=False):
    if not value: return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if dt.tzinfo: dt = dt.astimezone(WIB)
    base = f"{dt.day:02d} {BULAN[dt.month - 1]} {dt.year}"
    return f"{base} {dt.strftime('%H:%M')}" if with_time else base


def in_period(value, period, now):
    if period == "semua" or not value: return True
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    dt = dt.astimezone(WIB) if dt.tzinfo else dt
    if period == "harian": return dt.date() == now.date()
    if period == "bulanan": return (dt.year, dt.month) == (now.year, now.month)
    return True


def build_loans(transactions):
    loans, open_by_book = [], {}
    for t in sorted(transactions, key=lambda x: x["date"]):
        if t["action"] == "pinjam":
            loan = {"id": t["id"], "member_id": t["member_id"], "member_name": t["member_name"], "book_id": t["book_id"], "book_title": t["book_title"], "borrowed_at": t["date"], "returned_at": None, "status": "Dipinjam", "date": t["date"]}
            loans.append(loan); open_by_book.setdefault(t["book_id"], []).append(loan)
        else:
            stack = open_by_book.get(t["book_id"]) or []
            if stack:
                loan = stack.pop(0); loan.update(returned_at=t["date"], status="Dikembalikan")
            else:
                loans.append({"id": t["id"], "member_id": t["member_id"], "member_name": t["member_name"], "book_id": t["book_id"], "book_title": t["book_title"], "borrowed_at": None, "returned_at": t["date"], "status": "Dikembalikan", "date": t["date"]})
    loans.sort(key=lambda l: l["returned_at"] or l["borrowed_at"] or "", reverse=True)
    return loans


def _logo(value, fallback, size=16 * mm):
    try:
        if value and value.startswith("data:"):
            from PIL import Image as PILImage
            src = PILImage.open(io.BytesIO(base64.b64decode(value.split(",", 1)[1]))).convert("RGBA")
            bg = PILImage.new("RGBA", src.size, (255, 255, 255, 255)); bg.alpha_composite(src)
            out = io.BytesIO(); bg.convert("RGB").resize((180, 180)).save(out, format="JPEG", quality=88); out.seek(0)
            img = Image(out)
        else:
            img = Image(str(ASSETS / fallback))
        img.drawWidth = img.drawHeight = size
        return img
    except Exception:
        return Spacer(size, size)


def render_report_pdf(kind, period, rows, settings, officer):
    now = datetime.now(WIB)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=14 * mm, title=TITLES[kind])
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY, leading=18)
    sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#475569"), leading=12)
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, leading=11)
    cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")
    head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)

    kop = Table([[_logo(settings.get("school_logo"), "logo-sekolah.jpg"), [Paragraph("PERPUSTAKAAN SMA 1 NEGERI ABUNG TENGAH", h1), Paragraph("Jln Raya Subik, Desa Pekurun Selatan, Lampung Utara · Tanpa denda, budaya membaca", sub)], _logo(settings.get("library_logo"), "logo-perpustakaan.jpg")]], colWidths=[20 * mm, None, 20 * mm])
    kop.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, 0), 1.5, NAVY), ("BOTTOMPADDING", (0, 0), (-1, 0), 6)]))

    title = Paragraph(f"{TITLES[kind]} — {PERIODS.get(period, 'Semua waktu')}", ParagraphStyle("t", parent=h1, fontSize=13, spaceBefore=8))
    meta = Paragraph(f"Dicetak {fmt_long(now, True)} WIB · {len(rows)} baris · oleh {officer}", sub)

    if kind == "transaksi":
        header = ["No", "Anggota", "Buku", "Kode", "Tgl Pinjam", "Tgl Kembali", "Status"]
        widths = [10 * mm, 48 * mm, 70 * mm, 26 * mm, 36 * mm, 36 * mm, 28 * mm]
        body = [[str(i + 1), Paragraph(r["member_name"], cellb), Paragraph(r["book_title"], cell), r["book_id"], fmt_date(r["borrowed_at"], True), fmt_date(r["returned_at"], True), r["status"]] for i, r in enumerate(rows)]
        borrowed = sum(1 for r in rows if r["status"] == "Dipinjam"); summary = f"Total peminjaman: {len(rows)} · Masih dipinjam: {borrowed} · Dikembalikan: {len(rows) - borrowed}"
    elif kind == "masuk":
        header = ["No", "Judul Buku", "Penulis", "Jumlah", "Sumber", "Rak", "Tanggal", "Dicatat oleh"]
        widths = [10 * mm, 70 * mm, 45 * mm, 18 * mm, 32 * mm, 16 * mm, 30 * mm, 36 * mm]
        body = [[str(i + 1), Paragraph(r["title"], cellb), Paragraph(r.get("author", "-"), cell), f"{r['quantity']} eks", r.get("source") or "-", r.get("shelf", "-"), fmt_date(r["date"]), Paragraph(r.get("recorded_by", "-"), cell)] for i, r in enumerate(rows)]
        summary = f"Total penerimaan: {len(rows)} · Total eksemplar: {sum(r.get('quantity', 0) for r in rows)}"
    else:
        header = ["No", "Judul Buku", "Kode", "Catatan", "Tgl Lapor", "Status", "Ditemukan", "Pelapor"]
        widths = [10 * mm, 62 * mm, 24 * mm, 56 * mm, 30 * mm, 22 * mm, 30 * mm, 30 * mm]
        body = [[str(i + 1), Paragraph(r["title"], cellb), r["code"], Paragraph(r.get("detail") if r.get("detail") != r.get("code") else "-", cell), fmt_date(r["date"]), r["status"], fmt_date(r.get("found_at")), Paragraph(r.get("reported_by", "-"), cell)] for i, r in enumerate(rows)]
        lost = sum(1 for r in rows if r["status"] == "Hilang"); summary = f"Total laporan: {len(rows)} · Masih hilang: {lost} · Ditemukan: {len(rows) - lost}"

    if not body: body = [["", Paragraph("Belum ada data pada periode ini", cell)] + [""] * (len(header) - 2)]
    table = Table([[Paragraph(h, head) for h in header]] + body, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")), ("FONTSIZE", (0, 1), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))

    sign = Table([["", Paragraph(f"Pekurun Selatan, {fmt_long(now)}<br/>Petugas Perpustakaan,<br/><br/><br/><br/><b>{officer}</b>", ParagraphStyle("s", parent=cell, alignment=1))]], colWidths=[None, 70 * mm])
    doc.build([kop, title, meta, Spacer(1, 4), Paragraph(summary, ParagraphStyle("sum", parent=sub, textColor=BLUE, fontName="Helvetica-Bold")), Spacer(1, 6), table, Spacer(1, 14), sign])
    return buf.getvalue()
