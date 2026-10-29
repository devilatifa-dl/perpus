import { useEffect, useState } from "react";
import { PrintButton } from "./ReportPrint";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CalendarDays, Clock, Download, FileSpreadsheet, TrendingUp, UserCheck, Users } from "lucide-react";
import { api, fmtDate } from "../lib";
import { fmtDur } from "./Visitors";

export const STAT_PERIODS = [["harian", "Hari ini"], ["7hari", "7 hari"], ["30hari", "30 hari"], ["bulanan", "Bulan ini"], ["semua", "Semua"]];
const COLORS = ["#7c3aed", "#16a34a", "#d97706", "#7c3aed", "#db2777", "#0891b2", "#65a30d", "#dc2626"];

export function VisitStats({ download, downloading }) {
  const [period, setPeriod] = useState("7hari"); const [st, setSt] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { setErr(""); api.get("/visits/stats", { params: { period } }).then((r) => setSt(r.data)).catch(() => setErr("Statistik belum dapat dimuat")); }, [period]);
  const label = STAT_PERIODS.find((p) => p[0] === period)?.[1];
  const days = (st?.per_day || []).map((d) => ({ ...d, label: new Date(d.date + "T00:00:00").toLocaleDateString("id-ID", { day: "numeric", month: "short" }) }));
  const maxClass = Math.max(1, ...(st?.per_class || []).map((c) => c.count));
  return <div className="visit-stats-page" data-testid="visit-stats">
    <div className="stats-head">
      <div className="period-select" data-testid="stats-period">{STAT_PERIODS.map(([k, l]) => <button key={k} data-testid={`stats-period-${k}`} className={period === k ? "active" : ""} onClick={() => setPeriod(k)}>{l}</button>)}</div>
      <div className="download-row"><PrintButton/><button className="secondary" data-testid="stats-download-pdf" disabled={!!downloading} onClick={() => download("pdf", "statistik", period)}><Download size={16}/> {downloading === "pdf" ? "Menyiapkan..." : "PDF"}</button><button className="secondary" data-testid="stats-download-xlsx" disabled={!!downloading} onClick={() => download("xlsx", "statistik", period)}><FileSpreadsheet size={16}/> {downloading === "xlsx" ? "Menyiapkan..." : "Excel"}</button></div>
    </div>
    {err && <div className="error">{err}</div>}
    {!st && !err && <div className="panel muted">Menghitung statistik...</div>}
    {st && <>
      <div className="stats-kpis">
        <div className="kpi" data-testid="stats-total"><span className="kpi-icon blue"><Users size={18}/></span><small>Total pengunjung</small><b>{st.total}</b><em>{label}</em></div>
        <div className="kpi" data-testid="stats-avg"><span className="kpi-icon green"><TrendingUp size={18}/></span><small>Rata-rata per hari</small><b>{st.avg_per_day}</b><em>dari {st.days} hari</em></div>
        <div className="kpi" data-testid="stats-unique"><span className="kpi-icon orange"><UserCheck size={18}/></span><small>Anggota berbeda</small><b>{st.unique_members}</b><em>siswa/guru berkartu</em></div>
        <div className="kpi" data-testid="stats-duration"><span className="kpi-icon violet"><Clock size={18}/></span><small>Lama rata-rata</small><b>{fmtDur(st.avg_duration_min)}</b><em>{st.peak_hour != null ? `Jam ramai ${String(st.peak_hour).padStart(2, "0")}.00` : "belum ada data"}</em></div>
      </div>
      <div className="stats-grid">
        <div className="panel" data-testid="stats-per-day"><div className="panel-title"><div><p className="eyebrow">PENGUNJUNG PER HARI</p><h3>{st.peak_day && st.total ? <>Paling ramai {fmtDate(st.peak_day.date)} · {st.peak_day.total} orang</> : "Belum ada pengunjung"}</h3></div><CalendarDays size={18} color="#94a3b8"/></div>
          <div style={{ width: "100%", height: 260 }}><ResponsiveContainer initialDimension={{ width: 520, height: 260 }}><BarChart data={days} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0"/><XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} interval="preserveStartEnd"/><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }}/><Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }}/><Legend wrapperStyle={{ fontSize: 12 }}/><Bar dataKey="anggota" name="Anggota" stackId="a" fill="#7c3aed" radius={[0, 0, 0, 0]}/><Bar dataKey="tamu" name="Tamu" stackId="a" fill="#f59e0b" radius={[4, 4, 0, 0]}/></BarChart></ResponsiveContainer></div>
        </div>
        <div className="panel" data-testid="stats-kinds"><div className="panel-title"><div><p className="eyebrow">PERSENTASE PENGUNJUNG</p><h3>Anggota vs tamu</h3></div></div>
          <div style={{ width: "100%", height: 180 }}><ResponsiveContainer initialDimension={{ width: 520, height: 180 }}><PieChart><Pie data={st.kinds.filter((k) => k.count > 0).length ? st.kinds : [{ label: "Kosong", count: 1 }]} dataKey="count" nameKey="label" innerRadius={48} outerRadius={74} paddingAngle={2}>{(st.kinds.filter((k) => k.count > 0).length ? st.kinds : [{}]).map((k, i) => <Cell key={i} fill={st.total ? ["#7c3aed", "#f59e0b"][i] : "#e2e8f0"}/>)}</Pie><Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }}/></PieChart></ResponsiveContainer></div>
          <div className="pct-list">{st.kinds.map((k, i) => <div key={k.label} data-testid={`stats-kind-${k.label.toLowerCase()}`}><i style={{ background: ["#7c3aed", "#f59e0b"][i] }}/><span>{k.label}</span><b>{k.pct}%</b><small>{k.count}</small></div>)}</div>
          <p className="eyebrow" style={{ marginTop: 16 }}>CARA KELUAR</p>
          <div className="pct-list">{st.checkout_types.map((t, i) => <div key={t.key} data-testid={`stats-out-${t.key}`}><i style={{ background: ["#16a34a", "#64748b", "#d97706"][i] }}/><span>{t.label}</span><b>{t.pct}%</b><small>{t.count}</small></div>)}</div>
        </div>
      </div>
      <div className="stats-grid">
        <div className="panel" data-testid="stats-per-class"><div className="panel-title"><div><p className="eyebrow">PENGUNJUNG PER KELAS</p><h3>{st.per_class.length} kelas / kelompok</h3></div></div>
          {st.per_class.length === 0 && <p className="muted">Belum ada pengunjung pada periode ini.</p>}
          <div className="class-bars">{st.per_class.map((c, i) => <div className="class-bar" key={c.class_name} data-testid={`stats-class-${c.class_name.replaceAll(" ", "-")}`}>
            <div className="class-bar-label"><b>{c.class_name}</b><span>{c.count} pengunjung</span></div>
            <div className="class-bar-track"><div style={{ width: `${(c.count / maxClass) * 100}%`, background: c.class_name === "Tamu" ? "#f59e0b" : COLORS[i % COLORS.length] }}/></div>
            <em>{c.pct}%</em>
          </div>)}</div>
        </div>
        <div className="panel" data-testid="stats-per-hour"><div className="panel-title"><div><p className="eyebrow">JAM KEDATANGAN</p><h3>Sebaran per jam</h3></div></div>
          <div style={{ width: "100%", height: 240 }}><ResponsiveContainer initialDimension={{ width: 520, height: 240 }}><BarChart data={st.per_hour.map((h) => ({ ...h, label: `${String(h.hour).padStart(2, "0")}` }))} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0"/><XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }}/><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }}/><Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} labelFormatter={(l) => `Pukul ${l}.00`}/><Bar dataKey="count" name="Pengunjung" fill="#16a34a" radius={[4, 4, 0, 0]}/></BarChart></ResponsiveContainer></div>
        </div>
      </div>
      <div className="panel table-panel"><div className="panel-title"><div><p className="eyebrow">RINCIAN HARIAN</p><h3>Jumlah &amp; persentase per hari</h3></div></div>
        <div className="table-wrap"><table><thead><tr><th>TANGGAL</th><th>TOTAL</th><th>ANGGOTA</th><th>TAMU</th><th>PERSENTASE</th></tr></thead><tbody>
          {[...st.per_day].reverse().map((d) => <tr key={d.date} data-testid={`stats-day-${d.date}`}><td><b>{new Date(d.date + "T00:00:00").toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</b></td><td>{d.total}</td><td>{d.anggota}</td><td>{d.tamu}</td><td><div className="inline-pct"><div className="class-bar-track"><div style={{ width: `${st.total ? (d.total / st.total) * 100 : 0}%` }}/></div><span>{st.total ? ((d.total / st.total) * 100).toFixed(1) : "0.0"}%</span></div></td></tr>)}
        </tbody></table></div>
      </div>
    </>}
  </div>;
}
