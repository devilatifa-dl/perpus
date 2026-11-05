import { useEffect, useState } from "react";
import { PrintButton } from "./ReportPrint";
import { Award, BookOpen, Crown, Download, DoorOpen, FileSpreadsheet, GraduationCap, Medal, Trophy, UserRound, Users } from "lucide-react";
import { api } from "../lib";

const MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const monthLabel = (k) => { const [y, m] = k.split("-"); return `${MONTHS[Number(m) - 1]} ${y}`; };
const initials = (n = "") => n.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
const MEDAL = ["gold", "silver", "bronze"];

// Dua jenis peringkat memakai tampilan yang sama; hanya sumber data & teksnya berbeda.
const KINDS = {
  kunjungan: {
    url: "/visits/leaderboard", exportType: "peringkat", key: "visits", total: "total_visits",
    eyebrow: "PERINGKAT RAJIN BERKUNJUNG",
    title: (l) => `Siapa paling rajin ke perpustakaan bulan ${l}?`,
    intro: (lb) => `${lb.total_visits} pengunjung anggota dari ${lb.active_students} siswa. Scan kartumu setiap datang agar tercatat!`,
    unit: "pengunjung", sub: (s) => `${s.days} hari`,
    listTitle: "Pengunjung paling rajin", classTop: "Kelas teraktif", classUnit: "pengunjung",
    me: (s) => <>Hebat! Kamu peringkat <b>#{s.rank}</b> bulan ini dengan {s.visits} pengunjung.</>,
    notMe: "Kamu belum masuk 10 besar bulan ini — ayo lebih sering berkunjung!",
    empty: (l) => `Belum ada pengunjung anggota di bulan ${l}`, emptyHint: "Peringkat muncul setelah siswa scan kartu di menu Pengunjung.",
    few: (n) => `Baru ${n} siswa yang berkunjung bulan ini.`,
  },
  pinjam: {
    url: "/loans/leaderboard", exportType: "peringkat-pinjam", key: "loans", total: "total_loans",
    eyebrow: "PERINGKAT RAJIN MEMINJAM",
    title: (l) => `Siapa paling rajin meminjam buku bulan ${l}?`,
    intro: (lb) => `${lb.total_loans} peminjaman buku oleh ${lb.active_students} siswa. Pinjam buku dengan kartumu agar tercatat!`,
    unit: "buku dipinjam", sub: (s) => `${s.books} judul · ${s.days} hari`,
    listTitle: "Peminjam paling rajin", classTop: "Kelas terajin", classUnit: "peminjaman",
    me: (s) => <>Hebat! Kamu peringkat <b>#{s.rank}</b> bulan ini dengan {s.loans} buku dipinjam.</>,
    notMe: "Kamu belum masuk 10 besar bulan ini — ayo pinjam dan baca lebih banyak buku!",
    empty: (l) => `Belum ada peminjaman buku di bulan ${l}`, emptyHint: "Peringkat muncul setelah siswa meminjam buku di menu Sirkulasi.",
    few: (n) => `Baru ${n} siswa yang meminjam bulan ini.`,
  },
};

// Teks khusus peringkat guru (guru dipisah dari siswa; tanpa peringkat kelas)
const GURU_TEXT = {
  kunjungan: {
    title: (l) => `Guru mana paling rajin ke perpustakaan bulan ${l}?`,
    intro: (lb) => `${lb.total_visits} kunjungan dari ${lb.active_students} guru. Scan kartu guru setiap datang agar tercatat!`,
    empty: (l) => `Belum ada kunjungan guru di bulan ${l}`, emptyHint: "Peringkat guru muncul setelah guru scan kartu di menu Pengunjung.",
    few: (n) => `Baru ${n} guru yang berkunjung bulan ini.`, listTitle: "Guru paling rajin berkunjung",
  },
  pinjam: {
    title: (l) => `Guru mana paling rajin meminjam buku bulan ${l}?`,
    intro: (lb) => `${lb.total_loans} peminjaman buku oleh ${lb.active_students} guru.`,
    empty: (l) => `Belum ada peminjaman buku oleh guru di bulan ${l}`, emptyHint: "Peringkat guru muncul setelah guru meminjam buku di menu Sirkulasi.",
    few: (n) => `Baru ${n} guru yang meminjam bulan ini.`, listTitle: "Guru paling rajin meminjam",
  },
};

export function AudienceSwitch({ value, onChange }) {
  return <div className="lb-switch lb-audience" role="radiogroup" aria-label="Peringkat siswa atau guru" data-testid="leaderboard-audience-switch">
    <button type="button" role="radio" aria-checked={value === "siswa"} className={value === "siswa" ? "active" : ""} data-testid="leaderboard-audience-siswa" onClick={() => onChange("siswa")}><GraduationCap size={15}/> Siswa</button>
    <button type="button" role="radio" aria-checked={value === "guru"} className={value === "guru" ? "active" : ""} data-testid="leaderboard-audience-guru" onClick={() => onChange("guru")}><UserRound size={15}/> Guru</button>
  </div>;
}

function Avatar({ s, size = 56 }) {
  return <div className="lb-avatar" style={{ width: size, height: size, fontSize: size / 2.8 }}>{s.photo ? <img src={s.photo} alt={s.name}/> : initials(s.name)}</div>;
}

export function LeaderboardSwitch({ value, onChange }) {
  return <div className="lb-switch" role="radiogroup" aria-label="Jenis peringkat" data-testid="leaderboard-kind-switch">
    <button type="button" role="radio" aria-checked={value === "kunjungan"} className={value === "kunjungan" ? "active" : ""} data-testid="leaderboard-kind-kunjungan" onClick={() => onChange("kunjungan")}><DoorOpen size={15}/> Rajin berkunjung</button>
    <button type="button" role="radio" aria-checked={value === "pinjam"} className={value === "pinjam" ? "active" : ""} data-testid="leaderboard-kind-pinjam" onClick={() => onChange("pinjam")}><BookOpen size={15}/> Rajin meminjam</button>
  </div>;
}

export function Leaderboard({ mode = "admin", kind = "kunjungan", meId = "", download, downloading, audience: audienceProp, onAudience }) {
  const [ownAudience, setOwnAudience] = useState("siswa");
  const audience = audienceProp || ownAudience; const setAudience = onAudience || setOwnAudience;
  const guru = audience === "guru";
  const base = KINDS[kind] || KINDS.kunjungan;
  const K = guru ? { ...base, ...GURU_TEXT[kind === "pinjam" ? "pinjam" : "kunjungan"], eyebrow: `${base.eyebrow} · GURU` } : { ...base, eyebrow: `${base.eyebrow} · SISWA` };
  const [month, setMonth] = useState(""); const [lb, setLb] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { setLb(null); setMonth(""); }, [kind]);
  useEffect(() => { setLb(null); }, [audience]);
  useEffect(() => {
    let alive = true; setErr("");
    api.get(K.url, { params: month ? { month, audience } : { audience } })
      .then((r) => { if (!alive) return; setLb(r.data); if (!month) setMonth(r.data.month); })
      .catch(() => alive && setErr("Peringkat belum dapat dimuat"));
    return () => { alive = false; };
  }, [month, K.url, audience]);
  const bar = <div className="lb-audience-bar" data-testid="leaderboard-audience-bar"><AudienceSwitch value={audience} onChange={setAudience}/><span>{guru ? "Peringkat khusus anggota guru" : "Peringkat siswa · guru tidak ikut dihitung"}</span></div>;
  if (err) return <>{bar}<div className="error" data-testid="leaderboard-error">{err}</div></>;
  if (!lb) return <>{bar}<div className="panel muted">Menghitung peringkat...</div></>;
  const val = (x) => x[K.key] || 0;
  const podium = lb.students.slice(0, 3); const rest = lb.students.slice(3);
  const me = meId ? lb.students.find((s) => s.member_id === meId) : null;
  const maxCls = Math.max(1, ...lb.classes.map(val));
  const order = [1, 0, 2].filter((i) => podium[i]);
  return <>{bar}<div className={`leaderboard ${mode} kind-${kind} audience-${audience}`} data-testid={`leaderboard-${kind}`} data-audience={audience}>
    <div className="lb-hero">
      <div className="lb-hero-text"><p className="eyebrow light">{K.eyebrow}</p><h2 data-testid="leaderboard-title">{K.title(lb.label)}</h2><p>{K.intro(lb)}</p></div>
      <div className="lb-hero-actions">
        <select data-testid="leaderboard-month-select" value={month} onChange={(e) => setMonth(e.target.value)}>{lb.months.map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}</select>
        {mode === "admin" && download && <div className="download-row"><PrintButton/><button className="secondary" data-testid="leaderboard-download-pdf" disabled={!!downloading} onClick={() => download("pdf", K.exportType, lb.month, { audience })}><Download size={16}/> {downloading === "pdf" ? "Menyiapkan..." : "PDF"}</button><button className="secondary" data-testid="leaderboard-download-xlsx" disabled={!!downloading} onClick={() => download("xlsx", K.exportType, lb.month, { audience })}><FileSpreadsheet size={16}/> {downloading === "xlsx" ? "Menyiapkan..." : "Excel"}</button></div>}
      </div>
    </div>
    {mode === "siswa" && meId && (!guru || me) && <div className={`lb-me ${me ? "in" : ""}`} data-testid="leaderboard-me">{me ? <><Award size={18}/> {K.me(me)}</> : <><Trophy size={18}/> {K.notMe}</>}</div>}
    {lb.students.length === 0 ? <div className="panel lb-empty" data-testid="leaderboard-empty"><Trophy size={34}/><b>{K.empty(lb.label)}</b><span>{K.emptyHint}</span></div> : <>
      <div className="lb-podium" data-testid="leaderboard-podium">{order.map((i) => { const s = podium[i]; return <div key={s.member_id || s.name} className={`lb-step ${MEDAL[i]} ${s.member_id === meId ? "me" : ""}`} data-testid={`leaderboard-rank-${s.rank}`}>
        <div className="lb-medal">{i === 0 ? <Crown size={18}/> : <Medal size={16}/>}<span>#{s.rank}</span></div>
        <Avatar s={s} size={i === 0 ? 76 : 62}/>
        <b>{s.name}{s.member_id === meId ? " (kamu)" : ""}</b><small>{s.class_name}</small>
        <div className="lb-score"><strong>{val(s)}</strong><span>{K.unit} · {K.sub(s)}</span></div>
        <div className="lb-block"><span>{i + 1}</span></div>
      </div>; })}</div>
      <div className={`lb-grid${guru ? " single" : ""}`}>
        <div className="panel" data-testid="leaderboard-students"><div className="panel-title"><div><p className="eyebrow">{guru ? "10 BESAR GURU" : "10 BESAR SISWA"}</p><h3>{K.listTitle}</h3></div><Users size={18} color="#94a3b8"/></div>
          <div className="lb-list">{lb.students.map((s) => <div key={s.member_id || s.name} className={`lb-row ${s.member_id === meId ? "me" : ""}`} data-testid={`leaderboard-student-${s.rank}`}>
            <span className={`lb-rank ${MEDAL[s.rank - 1] || ""}`}>{s.rank}</span><Avatar s={s} size={36}/>
            <div className="lb-who"><b>{s.name}{s.member_id === meId ? " (kamu)" : ""}</b><small>{s.class_name}</small></div>
            <div className="lb-num"><b>{val(s)}</b><small>{K.sub(s)}{kind === "kunjungan" && mode === "admin" && s.minutes ? ` · ${Math.floor(s.minutes / 60)}j ${s.minutes % 60}m` : ""}</small></div>
          </div>)}</div>
          {rest.length === 0 && lb.students.length <= 3 && <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>{K.few(lb.students.length)}</p>}
        </div>
        {!guru && <div className="panel" data-testid="leaderboard-classes"><div className="panel-title"><div><p className="eyebrow">PERINGKAT KELAS</p><h3>{lb.classes[0] ? <>{K.classTop}: {lb.classes[0].class_name}</> : "-"}</h3></div><Trophy size={18} color="#d97706"/></div>
          <div className="class-bars">{lb.classes.map((c, i) => <div className="class-bar" key={c.class_name} data-testid={`leaderboard-class-${c.rank}`}>
            <div className="class-bar-label"><b>{c.rank <= 3 ? ["🥇", "🥈", "🥉"][c.rank - 1] + " " : `${c.rank}. `}{c.class_name}</b><span>{val(c)} {K.classUnit} · {c.members} siswa</span></div>
            <div className="class-bar-track"><div style={{ width: `${(val(c) / maxCls) * 100}%`, background: ["#d97706", "#64748b", "#b45309"][i] || "#7c3aed" }}/></div>
            <em>{c.pct}%</em>
          </div>)}</div>
        </div>}
      </div>
    </>}
  </div></>;
}

// Portal siswa: satu tab "Peringkat" dengan pilihan berkunjung / meminjam.
export function StudentLeaderboards({ meId }) {
  const [kind, setKind] = useState("kunjungan"); const [audience, setAudience] = useState("siswa");
  return <div className="lb-wrap" data-testid="student-leaderboards"><LeaderboardSwitch value={kind} onChange={setKind}/><Leaderboard mode="siswa" kind={kind} meId={meId} audience={audience} onAudience={setAudience}/></div>;
}
