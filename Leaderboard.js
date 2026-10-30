import { useEffect, useState } from "react";
import { PrintButton } from "./ReportPrint";
import { Award, Crown, Download, FileSpreadsheet, Medal, Trophy, Users } from "lucide-react";
import { api } from "../lib";

const MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const monthLabel = (k) => { const [y, m] = k.split("-"); return `${MONTHS[Number(m) - 1]} ${y}`; };
const initials = (n = "") => n.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
const MEDAL = ["gold", "silver", "bronze"];

function Avatar({ s, size = 56 }) {
  return <div className="lb-avatar" style={{ width: size, height: size, fontSize: size / 2.8 }}>{s.photo ? <img src={s.photo} alt={s.name}/> : initials(s.name)}</div>;
}

export function Leaderboard({ mode = "admin", meId = "", download, downloading, notify }) {
  const [month, setMonth] = useState(""); const [lb, setLb] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { setErr(""); api.get("/visits/leaderboard", { params: month ? { month } : {} }).then((r) => { setLb(r.data); if (!month) setMonth(r.data.month); }).catch(() => setErr("Peringkat belum dapat dimuat")); }, [month]);
  if (err) return <div className="error">{err}</div>;
  if (!lb) return <div className="panel muted">Menghitung peringkat...</div>;
  const podium = lb.students.slice(0, 3); const rest = lb.students.slice(3);
  const me = meId ? lb.students.find((s) => s.member_id === meId) : null;
  const maxCls = Math.max(1, ...lb.classes.map((c) => c.visits));
  const order = [1, 0, 2].filter((i) => podium[i]);
  return <div className={`leaderboard ${mode}`} data-testid="leaderboard">
    <div className="lb-hero">
      <div className="lb-hero-text"><p className="eyebrow light">PERINGKAT RAJIN BERKUNJUNG</p><h2>Siapa paling rajin ke perpustakaan bulan {lb.label}?</h2><p>{lb.total_visits} pengunjung anggota dari {lb.active_students} siswa. Scan kartumu setiap datang agar tercatat!</p></div>
      <div className="lb-hero-actions">
        <select data-testid="leaderboard-month-select" value={month} onChange={(e) => setMonth(e.target.value)}>{lb.months.map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}</select>
        {mode === "admin" && download && <div className="download-row"><PrintButton/><button className="secondary" data-testid="leaderboard-download-pdf" disabled={!!downloading} onClick={() => download("pdf", "peringkat", lb.month)}><Download size={16}/> {downloading === "pdf" ? "Menyiapkan..." : "PDF"}</button><button className="secondary" data-testid="leaderboard-download-xlsx" disabled={!!downloading} onClick={() => download("xlsx", "peringkat", lb.month)}><FileSpreadsheet size={16}/> {downloading === "xlsx" ? "Menyiapkan..." : "Excel"}</button></div>}
      </div>
    </div>
    {mode === "siswa" && meId && <div className={`lb-me ${me ? "in" : ""}`} data-testid="leaderboard-me">{me ? <><Award size={18}/> Hebat! Kamu peringkat <b>#{me.rank}</b> bulan ini dengan {me.visits} pengunjung.</> : <><Trophy size={18}/> Kamu belum masuk 10 besar bulan ini — ayo lebih sering berkunjung!</>}</div>}
    {lb.students.length === 0 ? <div className="panel lb-empty" data-testid="leaderboard-empty"><Trophy size={34}/><b>Belum ada pengunjung anggota di bulan {lb.label}</b><span>Peringkat muncul setelah siswa scan kartu di menu Pengunjung.</span></div> : <>
      <div className="lb-podium" data-testid="leaderboard-podium">{order.map((i) => { const s = podium[i]; return <div key={s.member_id || s.name} className={`lb-step ${MEDAL[i]} ${s.member_id === meId ? "me" : ""}`} data-testid={`leaderboard-rank-${s.rank}`}>
        <div className="lb-medal">{i === 0 ? <Crown size={18}/> : <Medal size={16}/>}<span>#{s.rank}</span></div>
        <Avatar s={s} size={i === 0 ? 76 : 62}/>
        <b>{s.name}{s.member_id === meId ? " (kamu)" : ""}</b><small>{s.class_name}</small>
        <div className="lb-score"><strong>{s.visits}</strong><span>pengunjung · {s.days} hari</span></div>
        <div className="lb-block"><span>{i + 1}</span></div>
      </div>; })}</div>
      <div className="lb-grid">
        <div className="panel" data-testid="leaderboard-students"><div className="panel-title"><div><p className="eyebrow">10 BESAR SISWA</p><h3>Pengunjung paling rajin</h3></div><Users size={18} color="#94a3b8"/></div>
          <div className="lb-list">{lb.students.map((s) => <div key={s.member_id || s.name} className={`lb-row ${s.member_id === meId ? "me" : ""}`} data-testid={`leaderboard-student-${s.rank}`}>
            <span className={`lb-rank ${MEDAL[s.rank - 1] || ""}`}>{s.rank}</span><Avatar s={s} size={36}/>
            <div className="lb-who"><b>{s.name}{s.member_id === meId ? " (kamu)" : ""}</b><small>{s.class_name}</small></div>
            <div className="lb-num"><b>{s.visits}</b><small>{s.days} hari{mode === "admin" && s.minutes ? ` · ${Math.floor(s.minutes / 60)}j ${s.minutes % 60}m` : ""}</small></div>
          </div>)}</div>
          {rest.length === 0 && lb.students.length <= 3 && <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>Baru {lb.students.length} siswa yang berkunjung bulan ini.</p>}
        </div>
        <div className="panel" data-testid="leaderboard-classes"><div className="panel-title"><div><p className="eyebrow">PERINGKAT KELAS</p><h3>{lb.classes[0] ? <>Kelas teraktif: {lb.classes[0].class_name}</> : "-"}</h3></div><Trophy size={18} color="#d97706"/></div>
          <div className="class-bars">{lb.classes.map((c, i) => <div className="class-bar" key={c.class_name} data-testid={`leaderboard-class-${c.rank}`}>
            <div className="class-bar-label"><b>{c.rank <= 3 ? ["🥇", "🥈", "🥉"][c.rank - 1] + " " : `${c.rank}. `}{c.class_name}</b><span>{c.visits} pengunjung · {c.members} siswa</span></div>
            <div className="class-bar-track"><div style={{ width: `${(c.visits / maxCls) * 100}%`, background: ["#d97706", "#64748b", "#b45309"][i] || "#7c3aed" }}/></div>
            <em>{c.pct}%</em>
          </div>)}</div>
        </div>
      </div>
    </>}
  </div>;
}
