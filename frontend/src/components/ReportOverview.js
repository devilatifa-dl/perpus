import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, BookOpen, ClipboardList, DoorOpen, FileSpreadsheet, Users } from "lucide-react";
import { api, fmt } from "../lib";

const todayWib = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);
const shift = (iso, days) => { const d = new Date(iso + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); };
const PRESETS = [["7", "7 hari"], ["30", "30 hari"], ["bulan", "Bulan ini"], ["tahun", "Tahun ini"]];

function presetRange(k) {
  const t = todayWib();
  if (k === "bulan") return [t.slice(0, 8) + "01", t, "day"];
  if (k === "tahun") return [t.slice(0, 5) + "01-01", t, "month"];
  return [shift(t, -(Number(k) - 1)), t, "day"];
}

const csvCell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
function downloadCsv(d) {
  const lines = [["Laporan ringkasan perpustakaan", `${d.start} s.d. ${d.end}`], [],
    ["RINGKASAN"], ["Total eksemplar", d.kpis.books], ["Judul buku", d.kpis.titles], ["Anggota", d.kpis.members], ["Peminjaman aktif", d.kpis.active_loans], ["Buku terlambat", d.kpis.overdue], ["Pengunjung hari ini", d.kpis.visits_today],
    ["Peminjaman pada rentang", d.totals.loans], ["Pengembalian pada rentang", d.totals.returns], ["Pengunjung pada rentang", d.totals.visits], [],
    [d.group === "month" ? "PER BULAN" : "PER HARI"], ["Periode", "Peminjaman", "Pengembalian", "Pengunjung"], ...d.series.map((s) => [s.key, s.loans, s.returns, s.visits]), [],
    ["BUKU TERPOPULER"], ["Peringkat", "Kode", "Judul", "Dipinjam"], ...d.top_books.map((b, i) => [i + 1, b.book_id, b.title, b.count]), [],
    ["ANGGOTA PALING AKTIF"], ["Peringkat", "Nama", "Kelas", "Peminjaman", "Pengunjung"], ...d.top_members.map((m, i) => [i + 1, m.name, m.class_name, m.loans, m.visits])];
  const blob = new Blob(["\ufeff" + lines.map((r) => r.map(csvCell).join(";")).join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `laporan-ringkasan-${d.start}-${d.end}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

function TopList({ title, eyebrow, rows, render, empty, testId }) {
  return <div className="panel" data-testid={testId}><div className="panel-title"><div><p className="eyebrow">{eyebrow}</p><h3>{title}</h3></div></div>
    {rows.length === 0 && <p className="muted">{empty}</p>}
    <ol className="top-list">{rows.map((r, i) => <li key={i} data-testid={`${testId}-item-${i}`}><span className={`top-rank r${i + 1}`}>{i + 1}</span>{render(r)}</li>)}</ol>
  </div>;
}

export function ReportOverview({ notify }) {
  const [range, setRange] = useState(() => presetRange("30")); const [preset, setPreset] = useState("30");
  const [d, setD] = useState(null); const [err, setErr] = useState("");
  const [start, end, group] = range;
  useEffect(() => { setErr(""); api.get("/reports/summary", { params: { start, end, group } }).then((r) => setD(r.data)).catch((e) => setErr(e.response?.data?.detail || "Laporan belum dapat dimuat")); }, [start, end, group]);
  const pick = (k) => { setPreset(k); setRange(presetRange(k)); };
  const setField = (i, v) => { if (!v) return; setPreset(""); setRange((r) => r.map((x, j) => (j === i ? v : x))); };
  const k = d?.kpis || {};
  const cards = [["Total buku", k.books, `${fmt(k.titles)} judul`, BookOpen, "blue", "kpi-books"], ["Anggota", k.members, "terdaftar", Users, "green", "kpi-members"], ["Peminjaman aktif", k.active_loans, "belum dikembalikan", ClipboardList, "orange", "kpi-active-loans"], ["Buku terlambat", k.overdue, "lewat batas pinjam", AlertTriangle, "red", "kpi-overdue"], ["Pengunjung hari ini", k.visits_today, "tercatat scan/tamu", DoorOpen, "blue", "kpi-visits-today"]];
  return <div className="report-overview" data-testid="report-overview">
    <div className="ro-filters">
      <div className="period-select" data-testid="ro-presets">{PRESETS.map(([key, l]) => <button key={key} data-testid={`ro-preset-${key}`} className={preset === key ? "active" : ""} onClick={() => pick(key)}>{l}</button>)}</div>
      <label className="ro-date">Dari<input type="date" data-testid="ro-start-input" value={start} max={end} onChange={(e) => setField(0, e.target.value)}/></label>
      <label className="ro-date">Sampai<input type="date" data-testid="ro-end-input" value={end} min={start} max={todayWib()} onChange={(e) => setField(1, e.target.value)}/></label>
      <div className="period-select" data-testid="ro-group">{[["day", "Per hari"], ["month", "Per bulan"]].map(([g, l]) => <button key={g} data-testid={`ro-group-${g}`} className={group === g ? "active" : ""} onClick={() => setRange([start, end, g])}>{l}</button>)}</div>
      <div className="download-row ro-actions">
        <button className="secondary" data-testid="ro-export-csv" disabled={!d} onClick={() => { downloadCsv(d); notify?.("Laporan CSV diunduh — bisa dibuka di Excel"); }}><FileSpreadsheet size={16}/> Excel / CSV</button>
      </div>
    </div>
    {err && <div className="error" data-testid="ro-error">{err}</div>}
    {!d && !err && <div className="panel muted">Menghitung laporan...</div>}
    {d && <>
      <p className="ro-range" data-testid="ro-range-label">Periode {new Date(d.start + "T00:00:00").toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })} – {new Date(d.end + "T00:00:00").toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}</p>
      <section className="stat-grid five">{cards.map(([label, value, sub, Icon, color, tid]) => <div className="stat-card" key={tid} data-testid={tid}><div className={`stat-icon ${color}`}><Icon size={19}/></div><span>{label}</span><strong>{fmt(value)}</strong><small>{sub}</small></div>)}</section>
      <div className="report-summary">
        <div><span>Peminjaman</span><b data-testid="ro-total-loans">{fmt(d.totals.loans)}</b><small>pada rentang ini</small></div>
        <div><span>Pengembalian</span><b data-testid="ro-total-returns">{fmt(d.totals.returns)}</b><small>pada rentang ini</small></div>
        <div><span>Pengunjung</span><b data-testid="ro-total-visits">{fmt(d.totals.visits)}</b><small>pada rentang ini</small></div>
      </div>
      <div className="ro-charts">
        <div className="panel" data-testid="ro-chart-loans"><div className="panel-title"><div><p className="eyebrow">SIRKULASI {group === "month" ? "PER BULAN" : "PER HARI"}</p><h3>Peminjaman &amp; pengembalian</h3></div></div>
          <div style={{ width: "100%", height: 260 }}><ResponsiveContainer><BarChart data={d.series} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0"/><XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd"/><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }}/><Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }}/><Legend wrapperStyle={{ fontSize: 12 }}/><Bar dataKey="loans" name="Peminjaman" fill="#7c3aed" radius={[4, 4, 0, 0]}/><Bar dataKey="returns" name="Pengembalian" fill="#16a34a" radius={[4, 4, 0, 0]}/></BarChart></ResponsiveContainer></div>
        </div>
        <div className="panel" data-testid="ro-chart-visits"><div className="panel-title"><div><p className="eyebrow">PENGUNJUNG {group === "month" ? "PER BULAN" : "PER HARI"}</p><h3>Tren pengunjung</h3></div></div>
          <div style={{ width: "100%", height: 260 }}><ResponsiveContainer><AreaChart data={d.series} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}><defs><linearGradient id="visGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#d97706" stopOpacity={0.35}/><stop offset="100%" stopColor="#d97706" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0"/><XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd"/><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }}/><Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }}/><Area type="monotone" dataKey="visits" name="Pengunjung" stroke="#d97706" strokeWidth={2} fill="url(#visGrad)"/></AreaChart></ResponsiveContainer></div>
        </div>
      </div>
      <div className="ro-charts">
        <TopList testId="ro-top-books" eyebrow="BUKU TERPOPULER" title="Paling sering dipinjam" rows={d.top_books} empty="Belum ada peminjaman pada rentang ini." render={(b) => <><div className="top-main"><b>{b.title}</b><small>{b.book_id}</small></div><em>{b.count}× dipinjam</em></>}/>
        <TopList testId="ro-top-members" eyebrow="ANGGOTA PALING AKTIF" title="Peminjaman + pengunjung" rows={d.top_members} empty="Belum ada aktivitas anggota pada rentang ini." render={(m) => <><div className="top-main"><b>{m.name}</b><small>{m.class_name || "-"}</small></div><em>{m.loans} pinjam · {m.visits} pengunjung</em></>}/>
      </div>
    </>}
  </div>;
}
