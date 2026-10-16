import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { BookOpen, Boxes, BookmarkPlus, ChevronRight } from "lucide-react";
import { Leaderboard } from "./Leaderboard";
import { fmtDate } from "../lib";
import { api, fmt, LIBRARY_LOGO, SCHOOL_LOGO } from "../lib";
import { Login } from "./Login";
import { Modal } from "./Modal";
import { PhotoBox } from "./PhotoBox";
import { MemberCard } from "./MemberCard";
import { Shelves } from "./Shelves";
import { StudentProfile } from "./StudentProfile";
import { uploadPhoto } from "../lib";
import { Lock, UserCircle } from "lucide-react";

const profileTab = ["profil", "Profil saya", UserCircle];
const tabs = [
  ["katalog", "Katalog buku", BookOpen],
  ["rak", "Rak buku", Boxes],
  ["profil", "Profil saya", UserCircle],
  ["peringkat", "Peringkat", Leaderboard],
  ["pesanan", "Pesanan", BookmarkPlus]
];

export default function StudentPortal() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState("katalog");
  const [data, setData] = useState({ books: [], shelves: [], mine: [], settings: {} });
  const [options, setOptions] = useState([]);
  const [meId, setMeId] = useState(() => localStorage.getItem("me_id") || "");
  const [meQuery, setMeQuery] = useState("");
  const [meOpen, setMeOpen] = useState(false);
  const [photoCfg, setPhotoCfg] = useState({ open: true, allowed: true });
  const [loadPhotoCfg, setLoadPhotoCfg] = useState(() => api.get("/settings/student-photo").catch(() => ({ open: true, allowed: true })));
  const [notify, setNotify] = useState(() => (t) => console.log(t));
  const [highlight, setHighlight] = useState(null);
  const [linked, setLinked] = useState(false);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [photoAllowed, setPhotoAllowed] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get("/students/me").then((res) => {
      setUser(res);
      setChecking(false);
    }).catch(() => {
      setChecking(false);
    });
  }, []);

  useEffect(() => {
    loadPhotoCfg.then((res) => {
      setPhotoAllowed(res?.allowed ?? true);
    });
  }, [loadPhotoCfg]);

  useEffect(() => {
    api.get("/catalog").then((res) => {
      setData((d) => ({ ...d, books: res.books || [], shelves: res.shelves || [] }));
    }).catch(() => {});
  }, []);

  if (checking) {
    return <div className="portal-loading">Memuat portal...</div>;
  }

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  const filtered = data.books.filter((b) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (b.title || "").toLowerCase().includes(q) || (b.author || "").toLowerCase().includes(q);
  });

  return (
    <div className="student-portal" data-testid="student-portal">
      <header className="portal-header">
        <div className="portal-brand">
          <img src={LIBRARY_LOGO || SCHOOL_LOGO} alt="Logo" className="portal-logo" />
          <h1>Portal Siswa Perpustakaan</h1>
        </div>
        <div className="portal-user">
          <span>{user.name}</span>
          <button className="btn btn-sm btn-outline" onClick={() => {
            localStorage.removeItem("token");
            setUser(null);
          }}>Keluar</button>
        </div>
      </header>

      <nav className="portal-nav">
        {tabs.map(([key, label, Icon]) => (
          <button
            key={key}
            className={`nav-tab ${tab === key ? "active" : ""}`}
            onClick={() => setTab(key)}
          >
            <Icon size={16} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <main className="portal-content">
        {tab === "katalog" && (
          <div className="catalog-tab">
            <div className="toolbar">
              <input
                type="text"
                placeholder="Cari judul atau penulis buku..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input search-input"
              />
            </div>
            <div className="catalog-grid">
              {filtered.map((b) => (
                <div className="catalog-item" key={b.id}>
                  <h4>{b.title}</h4>
                  <p className="muted">{b.author}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "profil" && <StudentProfile settings={data.settings} />}
        {tab === "rak" && <Shelves data={data} highlight={highlight} />}
        {tab === "peringkat" && <Leaderboard mode="siswa" meId={meId} />}
        
        {tab === "pesanan" && (
          <div className="my-reservations" data-testid="my-reservations">
            <p className="muted" style={{ marginTop: 0 }}>Pesanan diproses...</p>
            {data.mine.length === 0 && <div className="panel">Tidak ada pesanan</div>}
            {data.mine.map((r) => <div className="res-card" key={r.id}>{r.title}</div>)}
          </div>
        )}
      </main>

      {photoOpen && photoAllowed && (
        <Modal title="Unggah / ganti foto anggota" close={() => setPhotoOpen(false)}>
          <p className="account-hint" style={{ marginTop: 0 }}>Pilih foto terbaik Anda.</p>
          <PhotoBox value={user?.photo} upload={uploadPhoto} onChange={async (url) => {
            await api.patch("/students/me", { photo: url });
            setUser({ ...user, photo: url });
            setPhotoOpen(false);
          }} />
        </Modal>
      )}
    </div>
  );
}
