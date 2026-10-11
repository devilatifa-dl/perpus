import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { BookOpen, Boxes, ChevronRight, CreditCard, History, LogOut, Search, ShieldCheck } from "lucide-react";
import { api, fmt, LIBRARY_LOGO, SCHOOL_LOGO } from "../lib";
import { Login } from "./Login";
import { MemberCard } from "./MemberCard";
import { MemberHistory } from "./MemberHistory";
import { Shelves } from "./Shelves";

const tabs = [["katalog", "Katalog buku", BookOpen], ["rak", "Rak buku", Boxes], ["kartu", "Kartu saya", CreditCard], ["riwayat", "Riwayat saya", History]];

export default function StudentPortal() {
  const [user, setUser] = useState(null); const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState("katalog"); const [search, setSearch] = useState("");
  const [data, setData] = useState({ books: [], shelves: [], stats: {}, settings: null, member: null, memberError: "" });
  useEffect(() => { api.get("/auth/me").then((r) => setUser(r.data)).catch(() => {}).finally(() => setChecking(false)); }, []);
  useEffect(() => {
    if (!user || user.role !== "siswa") return;
    Promise.all([api.get("/books"), api.get("/shelves"), api.get("/dashboard"), api.get("/settings"), api.get("/members/me").catch((e) => ({ data: null, error: e.response?.data?.detail }))])
      .then(([b, s, d, c, m]) => setData({ books: b.data, shelves: s.data, stats: d.data, settings: c.data, member: m.data, memberError: m.error || "" }));
  }, [user]);
  if (checking) return <div className="loading">Membuka portal siswa...</div>;
  if (!user) return <Login onLogin={setUser} portal="siswa"/>;
  if (user.role !== "siswa") return <Navigate to="/admin" replace/>;
  const logout = async () => { await api.post("/auth/logout"); setUser(null); };
  const filtered = data.books.filter((b) => `${b.title} ${b.author} ${b.category} ${b.id}`.toLowerCase().includes(search.toLowerCase()));
  const available = data.books.filter((b) => b.status === "Tersedia").length;
  return <div className="student-shell" data-testid="student-portal" data-user-role="siswa">
    <header className="student-top">
      <div className="student-brand"><img src={data.settings?.library_logo || LIBRARY_LOGO} alt="Logo perpustakaan"/><div><strong>RUANG BACA · PORTAL SISWA</strong><small>SMA 1 NEGERI ABUNG TENGAH</small></div></div>
      <nav className="student-nav">{tabs.map(([id, label, Icon]) => <button key={id} data-testid={`student-tab-${id}`} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><Icon size={16}/><span>{label}</span></button>)}</nav>
      <div className="student-user"><img src={data.settings?.school_logo || SCHOOL_LOGO} alt="Logo sekolah"/><div><b>{user.name}</b><small>Akses baca-saja</small></div><button className="icon-button" data-testid="student-logout-button" title="Keluar" onClick={logout}><LogOut size={18}/></button></div>
    </header>
    <main className="student-main">
      <section className="student-hero">
        <div><p className="eyebrow light">HALO, {user.name.split(" ")[0].toUpperCase()}</p><h1>Buku apa yang ingin <em>kamu baca</em> hari ini?</h1><p>{fmt(available)} dari {fmt(data.stats.books)} buku tersedia untuk dipinjam. Datangi petugas dengan kartu anggotamu untuk meminjam — tanpa denda.</p></div>
        <div className="student-hero-badge"><ShieldCheck size={20}/><span>Tanpa denda</span></div>
      </section>
      {tab === "katalog" && <>
        <div className="toolbar"><div className="searchbox"><Search size={17}/><input data-testid="student-book-search-input" placeholder="Cari judul, penulis, atau kategori..." value={search} onChange={(e) => setSearch(e.target.value)}/></div><span className="soft-badge">{filtered.length} buku</span></div>
        <div className="catalog-grid">{filtered.map((b) => <div className="catalog-card" key={b.id} data-testid={`catalog-${b.id}`}><div className="catalog-cover">{b.cover ? <img src={b.cover} alt={b.title}/> : <BookOpen size={28}/>}</div><div className="catalog-info"><span className={`status ${b.status.toLowerCase()}`}>{b.status}</span><b>{b.title}</b><small>{b.author}</small><div className="catalog-meta"><span className="shelf-tag">Rak {b.shelf}</span><span>{b.category}</span></div></div></div>)}{filtered.length === 0 && <p className="muted">Tidak ada buku yang cocok.</p>}</div>
      </>}
      {tab === "rak" && <Shelves data={data}/>}
      {tab === "kartu" && <div className="student-card-wrap">{data.member ? <><MemberCard member={data.member} settings={data.settings}/><button className="secondary print-btn" data-testid="student-print-card-button" onClick={() => window.print()}><CreditCard size={17}/> Cetak kartu</button></> : <div className="panel" data-testid="student-no-member">{data.memberError || "Memuat kartu..."}</div>}</div>}
      {tab === "riwayat" && (data.member ? <MemberHistory member={data.member} refreshKey={0}/> : <div className="panel" data-testid="student-no-history">{data.memberError || "Memuat riwayat..."}</div>)}
    </main>
    <footer className="student-foot"><span>Jln Raya Subik, Desa Pekurun Selatan</span><span>Butuh bantuan? Hubungi petugas perpustakaan <ChevronRight size={12}/></span></footer>
  </div>;
}
