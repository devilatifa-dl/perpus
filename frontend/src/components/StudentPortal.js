import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { BookOpen, Boxes, BookmarkPlus, ChevronRight, ListChecks, LogOut, MapPin, Search, X } from "lucide-react";
import { fmtDate } from "../lib";
import { api, fmt, LIBRARY_LOGO, SCHOOL_LOGO } from "../lib";
import { Login } from "./Login";
import { Shelves } from "./Shelves";

const tabs = [["katalog", "Katalog buku", BookOpen], ["rak", "Rak buku", Boxes], ["pesanan", "Pesanan saya", ListChecks]];

export default function StudentPortal() {
  const [user, setUser] = useState(null); const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState("katalog"); const [search, setSearch] = useState(""); const [shelfFilter, setShelfFilter] = useState("semua"); const [highlight, setHighlight] = useState("");
  const [data, setData] = useState({ books: [], shelves: [], stats: {}, settings: null, mine: [] }); const [toast, setToast] = useState(""); const [busy, setBusy] = useState("");
  const notify = (t) => { setToast(t); setTimeout(() => setToast(""), 2800); };
  useEffect(() => { api.get("/auth/me").then((r) => setUser(r.data)).catch(() => {}).finally(() => setChecking(false)); }, []);
  const load = () => Promise.all([api.get("/books"), api.get("/shelves"), api.get("/dashboard"), api.get("/settings"), api.get("/reservations/mine")])
    .then(([b, s, d, c, m]) => setData({ books: b.data, shelves: s.data, stats: d.data, settings: c.data, mine: m.data }));
  useEffect(() => { if (user && user.role === "siswa") load(); }, [user]);
  const reserve = async (b) => { setBusy(b.id); try { await api.post("/reservations", { book_id: b.id }); await load(); notify(`“${b.title}” masuk antrean pesananmu`); } catch (e) { notify(e.response?.data?.detail || "Gagal memesan"); } finally { setBusy(""); } };
  const cancel = async (r) => { try { await api.delete(`/reservations/${r.id}`); await load(); notify("Pesanan dibatalkan"); } catch (e) { notify(e.response?.data?.detail || "Gagal membatalkan"); } };
  const waitingIds = new Set((data.mine || []).filter((r) => r.status === "Menunggu").map((r) => r.book_id));
  if (checking) return <div className="loading">Membuka portal siswa...</div>;
  if (!user) return <Login onLogin={setUser} portal="siswa"/>;
  if (user.role !== "siswa") return <Navigate to="/admin" replace/>;
  const logout = async () => { await api.post("/auth/logout"); setUser(null); };
  const filtered = data.books.filter((b) => (shelfFilter === "semua" || b.shelf === shelfFilter) && `${b.title} ${b.author} ${b.category} ${b.id}`.toLowerCase().includes(search.toLowerCase()));
  const shelfName = (id) => data.shelves.find((s) => s.id === id)?.name || "";
  const goToShelf = (id) => { setHighlight(id); setTab("rak"); };
  const available = data.books.filter((b) => b.status === "Tersedia").length;
  return <div className="student-shell" data-testid="student-portal" data-user-role="siswa">
    <header className="student-top">
      <div className="student-brand"><img src={data.settings?.library_logo || LIBRARY_LOGO} alt="Logo perpustakaan"/><div><strong>RUANG BACA · PORTAL SISWA</strong><small>SMA 1 NEGERI ABUNG TENGAH</small></div></div>
      <nav className="student-nav">{tabs.map(([id, label, Icon]) => <button key={id} data-testid={`student-tab-${id}`} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><Icon size={16}/><span>{label}</span></button>)}</nav>
      <div className="student-user"><img src={data.settings?.school_logo || SCHOOL_LOGO} alt="Logo sekolah"/><div><b>{user.name}</b><small>Hanya lihat data buku</small></div><button className="icon-button" data-testid="student-logout-button" title="Keluar" onClick={logout}><LogOut size={18}/></button></div>
    </header>
    <main className="student-main">
      <section className="student-hero">
        <div><p className="eyebrow light">HALO, {user.name.split(" ")[0].toUpperCase()}</p><h1>Buku apa yang ingin <em>kamu baca</em> hari ini?</h1><p>{fmt(available)} dari {fmt(data.stats.books)} buku tersedia untuk dipinjam. Datangi petugas perpustakaan untuk meminjam.</p></div>
      </section>
      {tab === "katalog" && <>
        <div className="toolbar"><div className="searchbox"><Search size={17}/><input data-testid="student-book-search-input" placeholder="Cari judul, penulis, atau kategori..." value={search} onChange={(e) => setSearch(e.target.value)}/></div><span className="soft-badge">{filtered.length} buku</span></div>
        <div className="shelf-chips" data-testid="shelf-chips"><button data-testid="shelf-chip-semua" className={shelfFilter === "semua" ? "active" : ""} onClick={() => setShelfFilter("semua")}>Semua rak</button>{data.shelves.map((s) => <button key={s.id} data-testid={`shelf-chip-${s.id}`} className={shelfFilter === s.id ? "active" : ""} onClick={() => setShelfFilter(s.id)}><MapPin size={12}/> {s.id} · {s.name}</button>)}</div>
        <div className="catalog-grid">{filtered.map((b) => <div className="catalog-card" key={b.id} data-testid={`catalog-${b.id}`}><div className="catalog-cover">{b.cover ? <img src={b.cover} alt={b.title}/> : <BookOpen size={28}/>}</div><div className="catalog-info"><span className={`status ${b.status.toLowerCase()}`}>{b.status}</span><b>{b.title}</b><small>{b.author}</small><div className="catalog-meta"><span>{b.category}</span><span>·</span><span>{b.id}</span></div><div className="catalog-shelf" data-testid={`catalog-shelf-${b.id}`}><MapPin size={13}/><span>Rak {b.shelf}{shelfName(b.shelf) ? ` · ${shelfName(b.shelf)}` : ""}</span><button data-testid={`goto-shelf-${b.id}`} onClick={() => goToShelf(b.shelf)}>Lihat rak</button></div>{b.status !== "Hilang" && (waitingIds.has(b.id) ? <button className="reserve-btn" disabled data-testid={`reserved-${b.id}`}><ListChecks size={14}/> Sudah dipesan</button> : <button className="reserve-btn" data-testid={`reserve-${b.id}`} disabled={busy === b.id} onClick={() => reserve(b)}><BookmarkPlus size={14}/> Pesan buku{b.waiting ? ` · ${b.waiting} antre` : ""}</button>)}</div></div>)}{filtered.length === 0 && <p className="muted">Tidak ada buku yang cocok.</p>}</div>
      </>}
      {tab === "rak" && <Shelves data={data} highlight={highlight}/>}
      {tab === "pesanan" && <div className="my-reservations" data-testid="my-reservations">
        <p className="muted" style={{ marginTop: 0 }}>Pesanan diproses petugas di meja sirkulasi. Datang membawa kartu anggotamu. Maksimal 3 pesanan aktif.</p>
        {data.mine.length === 0 && <div className="panel" data-testid="my-reservations-empty">Belum ada pesanan. Pilih buku di katalog lalu tekan “Pesan buku”.</div>}
        {data.mine.map((r) => <div className="res-card" key={r.id} data-testid={`my-reservation-${r.id}`}><div className="activity-icon borrow"><BookOpen size={15}/></div><div><b>{r.book_title}</b><span>Rak {r.book_shelf} · dipesan {fmtDate(r.created_at)}{r.processed_by ? ` · diproses ${r.processed_by}` : ""}</span></div><span className={`status ${r.status.toLowerCase()}`}>{r.status}</span>{r.status === "Menunggu" && <button className="icon-button" title="Batalkan" data-testid={`cancel-reservation-${r.id}`} onClick={() => cancel(r)}><X size={16}/></button>}</div>)}
      </div>}
    </main>
    {toast && <div className="toast" data-testid="toast-message">{toast}</div>}
    <footer className="student-foot"><span>Jln Raya Subik, Desa Pekurun Selatan</span><span>Butuh bantuan? Hubungi petugas perpustakaan <ChevronRight size={12}/></span></footer>
  </div>;
}
