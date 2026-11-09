import { useEffect, useState } from "react";
import { AlertTriangle, Clock, Download, FileSpreadsheet, Users } from "lucide-react";
import { api, fmt } from "../lib";
import { PrintButton } from "./ReportPrint";

const PERIODS = [["semua", "Semua"], ["harian", "Hari ini"], ["bulanan", "Bulan ini"]];

/**
 * Laporan peminjaman yang sudah lewat batas (dipinjam lebih dari N hari).
 * Menampilkan statistik ringkas, persentase per kelas, dan tombol cetak/PDF/Excel.
 */
export default function OverdueReport({ notify, download, downloading }) {
  const [period, setPeriod] = useState("semua");
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    setErr("");
    api.get("/reports/overdue", { params: { period } })
      .then((r) => { if (alive) setD(r.data); })
      .catch((e) => { if (alive) setErr(e.response?.data?.detail || "Laporan belum dapat dimuat"); });
    return () => { alive = false; };
  }, [period]);

  const items = d?.items || [];
  const perClass = d?.per_class || [];
  const total = d?.total || 0;

  return <div className="overdue-report" data-testid="overdue-report">
    <div className="ro-filters">
      <div className="period-select" data-testid="overdue-period">
        {PERIODS.map(([k, l]) => <button key={k} data-testid={`overdue-period-${k}`} className={period === k ? "active" : ""} onClick={() => setPeriod(k)}>{l}</button>)}
      </div>
      <div className="download-row ro-actions">
        <PrintButton/>
        <button className="secondary" data-testid="overdue-export-pdf" disabled={!d || !!downloading} onClick={() => download("pdf")}><Download size={16}/> {downloading === "pdf" ? "Menyiapkan..." : "PDF"}</button>
        <button className="secondary" data-testid="overdue-export-xlsx" disabled={!d || !!downloading} onClick={() => download("xlsx")}><FileSpreadsheet size={16}/> {downloading === "xlsx" ? "Menyiapkan..." : "Excel"}</button>
      </div>
    </div>

    {err && <div className="error" data-testid="overdue-error">{err}</div>}
    {!d && !err && <div className="panel muted">Menghitung laporan...</div>}

    {d && <>
      <section className="stat-grid three">
        <div className="stat-card" data-testid="overdue-kpi-total">
          <div className="stat-icon red"><AlertTriangle size={19}/></div>
          <span>Buku terlambat</span><strong>{fmt(total)}</strong>
          <small>dipinjam lebih dari {d.days} hari</small>
        </div>
        <div className="stat-card" data-testid="overdue-kpi-avg">
          <div className="stat-icon orange"><Clock size={19}/></div>
          <span>Rata-rata</span><strong>{d.avg_days}</strong>
          <small>hari per buku</small>
        </div>
        <div className="stat-card" data-testid="overdue-kpi-max">
          <div className="stat-icon blue"><Users size={19}/></div>
          <span>Terlama</span><strong>{d.max_days}</strong>
          <small>hari belum kembali</small>
        </div>
      </section>

      {perClass.length > 0 && <div className="panel" data-testid="overdue-per-class">
        <div className="panel-title"><div><p className="eyebrow">SEBARAN</p><h3>Per kelas</h3></div></div>
        <ul className="pct-list">
          {perClass.map((c) => <li key={c.class_name} data-testid={`overdue-class-${c.class_name}`}>
            <span className="pct-name">{c.class_name}</span>
            <span className="pct-bar"><i style={{ width: `${Math.max(2, c.pct)}%` }}/></span>
            <span className="pct-value">{c.count}<span className="print-hide"> · {c.pct.toFixed(1)}%</span></span>
          </li>)}
        </ul>
      </div>}

      <div className="panel table-panel" data-testid="overdue-table">
        <div className="panel-title"><div><p className="eyebrow">DAFTAR</p><h3>Peminjaman lewat batas</h3></div></div>
        {items.length === 0
          ? <p className="muted" data-testid="overdue-empty">Tidak ada peminjaman yang lewat {d.days} hari. Semua tepat waktu.</p>
          : <div className="table-wrap"><table>
            <thead><tr><th>ANGGOTA</th><th>KELAS</th><th>BUKU</th><th>TGL PINJAM</th><th>LAMA</th></tr></thead>
            <tbody>{items.map((r) => <tr key={r.id} data-testid={`overdue-row-${r.id}`}>
              <td><b>{r.member_name}</b></td>
              <td>{r.class_name || "-"}</td>
              <td><b>{r.book_title}</b><div className="print-hide" style={{ fontSize: 11, color: "#94a3b8" }}>{r.book_id}</div></td>
              <td>{new Date(r.borrowed_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" })}</td>
              <td><span className="days-pill">{r.days_out} hari</span></td>
            </tr>)}</tbody>
          </table></div>}
      </div>
    </>}
  </div>;
}
