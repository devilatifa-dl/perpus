import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { BookOpen, Boxes, BookmarkPlus, ChevronRight, ListChecks, LogOut, MapPin, Search, X, Camera } from "lucide-react";
import { fmtDate } from "../lib";
import { api, fmt, LIBRARY_LOGO, SCHOOL_LOGO } from "../lib";
import { Login } from "./Login";
import { Modal, PhotoBox } from "./Shared";
import { MemberCard } from "./MemberCard";
import { Shelves } from "./Shelves";

const tabs = [["katalog", "Katalog buku", BookOpen], ["rak", "Rak buku", Boxes], ["pesanan", "Pesanan saya", ListChecks]];

export default function StudentPortal() {
  const [user, setUser] = useState(null); const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState("katalog"); const [search, setSearch] = useState(""); const [shelfFilter, setShelfFilter] = useState("semua"); const [highlight, setHighlight] = useState("");
  const [data, setData] = useState({ books: [], shelves: [], stats: {}, settings: null, mine: [] }); const [toast, setToast] = useState(""); const [busy, setBusy] = useState("");
  const [options, setOptions] = useState([]); const [photoOpen, setPhotoOpen] = useState(false); const [savingPhoto, setSavingPhoto] = useState(false); const [selId, setSelId] = useState(""); const [draftPhoto, setDraftPhoto] = useState("");
  const [meId, setMeId] = useState(() => localStorage.getItem("perpus_me_id") || "");
  const notify = (t) => { setToast(t); setTimeout(() => setToast(""), 2800); };
  useEffect(() => { api.get("/auth/me").then((r) => setUser(r.data)).catch(() => {}).finally(() => setChecking(false)); }, []);
  const loadOptions = () => api.get("/members/options").then((r) => setOptions(r.data)).catch(() => {});
  const loadMine = (id) => api.get("/reservations/mine", { params: id ? { member_id: id } : {} }).then((r) => setData((d) => ({ ...d, mine: r.data }))).catch(() => {});
  const load = () => Promise.all([api.get("/books"), api.get("/shelves"), api.get("/dashboard"), api.get("/settings")])
    .then(([b, s, d, c]) => setData((prev) => ({ ...prev, books: b.data, shelves: s.data, stats: d.data, settings: c.data })));
  useEffect(() => { if (user && user.role === "siswa") { load(); loadOptions(); loadMine(meId); } }, [user]);
  const chooseMe = (id) => { setMeId(id); if (id) localStorage.setItem("perpus_me_id", id); else localStorage.removeItem("perpus_me_id"); loadMine(id); };
  const openPhoto = () => { loadOptions(); setSelId(meId || ""); setDraftPhoto((options.find((o) => o.id === meId) || {}).photo || ""); setPhotoOpen(true); };
  const chooseMember = (id) => { setSelId(id); const m = options.find((o) => o.id === id); setDraftPhoto(m?.photo || ""); };
  const savePhoto = async () => { if (!selId) { notify("Pilih nama anggota dulu"); return; } setSavingPhoto(true); try { await api.post(`/members/${selId}/photo`, { photo: draftPhoto }); await loadOptions(); notify("Foto disimpan — kartu anggota diperbarui"); } catch (e) { notify(e.response?.data?.detail || "Gagal menyimpan foto"); } finally { setSavingPhoto(false); } };
  const reserve = async (b) => { if (!meId) { notify("Pilih namamu dulu di bagian atas sebelum memesan"); return; } setBusy(b.id); try { await api.post("/reservations", { book_id: b.id, member_id: meId }); await Promise.all([load(), loadMine(meId)]); notify(`“${b.title}” masuk antrean pesanan`); } catch (e) { notify(e.response?.data?.detail || "Gagal memesan"); } finally { setBusy(""); } };
  const cancel = async (r) => { try { await api.delete(`/reservations/${r.id}`, { params: meId ? { member_id: meId } : {} }); await Promise.all([load(), loadMine(meId)]); notify("Pesanan dibatalkan"); } catch (e) { notify(e.response?.data?.detail || "Gagal membatalkan"); } };
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
        <div><p className="eyebrow light">HALO, PINTAR</p><h1>Buku apa yang ingin <em>kamu baca</em> hari ini?</h1><p>{fmt(available)} dari {fmt(data.stats.books)} buku tersedia untuk dipinjam. Datangi petugas perpustakaan untuk meminjam.</p></div>
        <div className="student-profile" data-testid="student-profile">
          <div className="student-profile-avatar"><Camera size={26}/></div>
          <button className="reserve-btn" data-testid="open-photo-upload-button" onClick={openPhoto}><Camera size={14}/> Unggah foto anggota</button>
        </div>
      </section>
      <div className="student-identity" data-testid="student-identity">
        <span className="identity-label">Pesan buku atas nama:</span>
        <select data-testid="identity-select" value={meId} onChange={(e) => chooseMe(e.target.value)}>
          <option value="">— Pilih namamu —</option>
          {options.map((o) => <option key={o.id} value={o.id}>{o.name}{o.class_name ? ` · ${o.class_name}` : ""}</option>)}
        </select>
        {meId ? <span className="identity-current" data-testid="identity-current">Halo, {options.find((o) => o.id === meId)?.name || ""} 👋</span> : <span className="identity-hint">Pilih namamu dulu agar petugas tahu siapa yang memesan</span>}
      </div>
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
    {photoOpen && <Modal title="Unggah / ganti foto anggota" close={() => { setPhotoOpen(false); setSelId(""); setDraftPhoto(""); }}>
      <p className="account-hint" style={{ marginTop: 0 }}>Pilih nama anggota, lalu unggah atau ganti fotonya. Kartu anggota akan otomatis memakai foto terbaru.</p>
      <label className="photo-member-select">Nama anggota
        <select data-testid="photo-member-select" value={selId} onChange={(e) => chooseMember(e.target.value)}>
          <option value="">— Pilih nama anggota —</option>
          {options.map((o) => <option key={o.id} value={o.id}>{o.name}{o.class_name ? ` · ${o.class_name}` : ""}</option>)}
        </select>
      </label>
      {options.length === 0 && <p className="muted">Belum ada data anggota. Hubungi petugas perpustakaan.</p>}
      {selId ? <>
        <PhotoBox value={draftPhoto} onChange={setDraftPhoto} label="Foto anggota" testId="student-photo-box"/>
        <div className="photo-card-preview"><p className="eyebrow">PRATINJAU KARTU</p><MemberCard member={{ ...options.find((o) => o.id === selId), photo: draftPhoto }} settings={data.settings}/></div>
        <button className="primary full" data-testid="save-student-photo-button" disabled={savingPhoto} onClick={savePhoto}>{savingPhoto ? "Menyimpan..." : "Simpan foto"}</button>
      </> : <p className="muted">Pilih nama anggota untuk mulai mengunggah foto.</p>}
    </Modal>}
    {toast && <div className="toast" data-testid="toast-message">{toast}</div>}
    <footer className="student-foot"><span>Jln Raya Subik, Desa Pekurun Selatan</span><span>Butuh bantuan? Hubungi petugas perpustakaan <ChevronRight size={12}/></span></footer>
  </div>;
}
