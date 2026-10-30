import { useEffect, useState } from "react";
import { PrintButton } from "./ReportPrint";
import { BookOpen, Crown, Download, FileSpreadsheet, Medal, Trophy } from "lucide-react";
import { api } from "../lib";

const MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const monthLabel = (k) => { const [y, m] = k.split("-"); return `${MONTHS[Number(m) - 1]} ${y}`; };
const initials = (n = "") => n.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
const MEDAL = ["gold", "silver", "bronze"];

function Avatar({ s, size = 56 }) {
  return <div className="lb-avatar" style={{ width: size, height: size, fontSize: size / 2.8 }}>{s.photo ? <img src={s.photo} alt={s.name}/> : initials(s.name)}</div>;
}

function Podium({ students }) {
  const order = [1, 0, 2].filter((i) => students[i]);
  return <div className="lb-podium" data-testid="loan-leaderboard-podium">{order.map((i) => { const s = students[i]; return <div key={s.member_id} className={`lb-step ${MEDAL[i]}`} data-testid={`loan-leaderboard-rank-${s.rank}`}>
    <div className="lb-medal">{i === 0 ? <Crown size={18}/> : <Medal size={16}/>}<span>#{s.rank}</span></div>
    <Avatar s={s} size={i === 0 ? 76 : 62}/>
    <b>{s.name}</b><small>{s.class_name}</small>
    <div className="lb-score"><strong>{s.loans}</strong><span>pinjam · {s.titles} judul</span></div>
    <div className="lb-block"><span>{i + 1}</span></div>
  </div>; })}</div>;
}

function StudentList({ students }) {
  return <div className="panel" data-testid="loan-leaderboard-students"><div className="panel-title"><div><p className="eyebrow">10 BESAR SISWA</p><h3>Peminjam paling rajin</h3></div><BookOpen size={18} color="#94a3b8"/></div>
    <div className="lb-list">{students.map((s) => <div key={s.member_id} className="lb-row" data-testid={`loan-leaderboard-student-${s.rank}`}>
      <span className={`lb-rank ${MEDAL[s.rank - 1] || ""}`}>{s.rank}</span><Avatar s={s} size={36}/>
      <div className="lb-who"><b>{s.name}</b><small>{s.class_name}</small></div>
      <div className="lb-num"><b>{s.loans}</b><small>{s.titles} judul · {s.pct}%</small></div>
    </div>)}</div>
    {students.length <= 3 && <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>Baru {students.length} siswa yang meminjam bulan ini.</p>}
  </div>;
}

function ClassBars({ classes }) {
  const max = Math.max(1, ...classes.map((c) => c.loans));
  return <div className="panel" data-testid="loan-leaderboard-classes"><div className="panel-title"><div><p className="eyebrow">PERINGKAT KELAS</p><h3>{classes[0] ? <>Kelas paling rajin meminjam: {classes[0].class_name}</> : "-"}</h3></div><Trophy size={18} color="#d97706"/></div>
    <div className="class-bars">{classes.map((c, i) => <div className="class-bar" key={c.class_name} data-testid={`loan-leaderboard-class-${c.rank}`}>
      <div className="class-bar-label"><b>{c.rank}. {c.class_name}</b><span>{c.loans} peminjaman · {c.members} siswa</span></div>
      <div className="class-bar-track"><div style={{ width: `${(c.loans / max) * 100}%`, background: ["#d97706", "#64748b", "#b45309"][i] || "#7c3aed" }}/></div>
      <em>{c.pct}%</em>
    </div>)}</div>
  </div>;
}

export function LoanLeaderboard({ download, downloading }) {
  const [month, setMonth] = useState(""); const [lb, setLb] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { setErr(""); api.get("/reports/loan-leaderboard", { params: month ? { month } : {} }).then((r) => { setLb(r.data); if (!month) setMonth(r.data.month); }).catch(() => setErr("Peringkat peminjam belum dapat dimuat")); }, [month]);
  if (err) return <div className="error" data-testid="loan-leaderboard-error">{err}</div>;
  if (!lb) return <div className="panel muted">Menghitung peringkat...</div>;
  return <div className="leaderboard admin" data-testid="loan-leaderboard">
    <div className="lb-hero">
      <div className="lb-hero-text"><p className="eyebrow light">PERINGKAT RAJIN MEMINJAM BUKU</p><h2>Siapa paling rajin meminjam buku bulan {lb.label}?</h2><p data-testid="loan-leaderboard-summary">{lb.total_loans} peminjaman oleh {lb.active_students} siswa.</p></div>
      <div className="lb-hero-actions">
        <select data-testid="loan-leaderboard-month-select" value={month} onChange={(e) => setMonth(e.target.value)}>{lb.months.map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}</select>
        <div className="download-row"><PrintButton/><button className="secondary" data-testid="loan-leaderboard-download-pdf" disabled={!!downloading} onClick={() => download("pdf", "peminjam", lb.month)}><Download size={16}/> {downloading === "pdf" ? "Menyiapkan..." : "PDF"}</button><button className="secondary" data-testid="loan-leaderboard-download-xlsx" disabled={!!downloading} onClick={() => download("xlsx", "peminjam", lb.month)}><FileSpreadsheet size={16}/> {downloading === "xlsx" ? "Menyiapkan..." : "Excel"}</button></div>
      </div>
    </div>
    {lb.students.length === 0 ? <div className="panel lb-empty" data-testid="loan-leaderboard-empty"><Trophy size={34}/><b>Belum ada peminjaman di bulan {lb.label}</b><span>Peringkat muncul setelah siswa meminjam buku di menu Sirkulasi.</span></div> : <>
      <Podium students={lb.students.slice(0, 3)}/>
      <div className="lb-grid"><StudentList students={lb.students}/><ClassBars classes={lb.classes}/></div>
    </>}
  </div>;
}
