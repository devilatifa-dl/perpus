import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { BarChart3, BookOpen, Boxes, Camera, ChevronRight, ClipboardList, CreditCard, LayoutDashboard, LogOut, Menu, Plus, QrCode, Search, ShieldCheck, Trash2, Upload, Users, X, ScanLine } from "lucide-react";
import { Html5Qrcode } from "html5-qrcode";
import "@/App.css";
import "@/Fixes.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const api = axios.create({ baseURL: API, withCredentials: true });
const fmt = (value) => new Intl.NumberFormat("id-ID").format(value || 0);

const readFile = (file) => new Promise((resolve, reject) => {
  if (!file) return resolve("");
  if (file.size > 900 * 1024) return reject(new Error("Ukuran maksimal 900KB"));
  const r = new FileReader(); r.onload = () => resolve(r.result); r.onerror = reject; r.readAsDataURL(file);
});

function Login({ onLogin }) {
  const [email, setEmail] = useState("admin@smansa.sch.id"); const [password, setPassword] = useState("admin123"); const [error, setError] = useState("");
  const submit = async (e) => { e.preventDefault(); try { const { data } = await api.post("/auth/login", { email, password }); onLogin(data); } catch (err) { setError(err.response?.data?.detail || "Email atau kata sandi salah"); } };
  const demo = (role) => { const v = { admin:["admin@smansa.sch.id","admin123"], petugas:["petugas@smansa.sch.id","petugas123"], siswa:["siswa@smansa.sch.id","siswa123"] }; setEmail(v[role][0]); setPassword(v[role][1]); setError(""); };
  return <main className="login-shell"><div className="login-visual"><div className="brand-mark"><BookOpen size={22}/></div><p className="overline">PORTAL PERPUSTAKAAN SEKOLAH</p><h1>Temukan pengetahuan,<br/><em>mulai dari sini.</em></h1><p className="login-copy">Satu ruang digital untuk merawat koleksi, melayani siswa, dan menjaga budaya membaca.</p><div className="login-address"><span>SMA 1 NEGERI ABUNG TENGAH</span><span>Jln Raya Subik, Desa Pekurun Selatan</span></div></div><div className="login-panel"><div className="login-panel-inner"><p className="eyebrow">SELAMAT DATANG KEMBALI</p><h2>Masuk ke ruang kerja</h2><p className="muted">Gunakan akun sekolah Anda untuk melanjutkan.</p><form onSubmit={submit} data-testid="login-form"><label>Email sekolah<input data-testid="login-email-input" value={email} onChange={e=>setEmail(e.target.value)} type="email" required/></label><label>Kata sandi<input data-testid="login-password-input" value={password} onChange={e=>setPassword(e.target.value)} type="password" required/></label>{error&&<div className="error" data-testid="login-error">{error}</div>}<button className="primary full" data-testid="login-submit-button">Masuk ke dashboard <ChevronRight size={17}/></button></form><div className="demo-login"><span>AKSES DEMO CEPAT</span><div>{["admin","petugas","siswa"].map(role=><button key={role} data-testid={`demo-login-${role}-button`} onClick={()=>demo(role)}>{role}</button>)}</div></div></div></div></main>
}

const nav = [{id:"overview", label:"Ringkasan", icon:LayoutDashboard},{id:"books",label:"Koleksi buku",icon:BookOpen},{id:"members",label:"Anggota",icon:Users},{id:"shelves",label:"Rak buku",icon:Boxes},{id:"circulation",label:"Sirkulasi",icon:QrCode},{id:"reports",label:"Laporan",icon:BarChart3}];

function App() {
  const [user,setUser]=useState(null); const [checking,setChecking]=useState(true); const [view,setView]=useState("overview"); const [mobileOpen,setMobileOpen]=useState(false); const [data,setData]=useState({books:[],members:[],shelves:[],transactions:[],reports:{incoming:[],missing:[]},stats:{}}); const [toast,setToast]=useState("");
  const load = async () => { const [stats,books,members,shelves,transactions,reports] = await Promise.all([api.get("/dashboard"),api.get("/books"),api.get("/members"),api.get("/shelves"),api.get("/transactions"),api.get("/reports")]); setData({stats:stats.data,books:books.data,members:members.data,shelves:shelves.data,transactions:transactions.data,reports:reports.data}); };
  useEffect(()=>{api.get("/auth/me").then(r=>setUser(r.data)).catch(()=>{}).finally(()=>setChecking(false));},[]);
  useEffect(()=>{if(user) load().catch(()=>setToast("Data belum dapat dimuat"));},[user]);
  if(checking) return <div className="loading">Membuka perpustakaan...</div>; if(!user) return <Login onLogin={setUser}/>;
  const logout=async()=>{await api.post("/auth/logout");setUser(null)}; const notify=(text)=>{setToast(text);setTimeout(()=>setToast(""),2800)};
  return <div className="app-frame" data-user-role={user.role}><aside className={mobileOpen?"sidebar mobile-open":"sidebar"}><div className="side-brand"><div className="logo-box"><BookOpen size={20}/></div><div><strong>RUANG BACA</strong><small>SMANSA ABUNG TENGAH</small></div></div><div className="side-label">MENU UTAMA</div><nav>{nav.map(item=>{const Icon=item.icon;return <button key={item.id} data-testid={`nav-${item.id}-button`} className={view===item.id?"nav-item active":"nav-item"} onClick={()=>{setView(item.id);setMobileOpen(false)}}><Icon size={18}/><span>{item.label}</span>{view===item.id&&<ChevronRight size={15}/>}</button>})}</nav><div className="side-bottom"><div className="no-fine"><ShieldCheck size={18}/><div><b>Tanpa denda</b><small>Belajar tetap nyaman</small></div></div><button className="logout" data-testid="logout-button" onClick={logout}><LogOut size={17}/> Keluar</button></div></aside><div className="content"><header className="topbar"><button className="mobile-menu" data-testid="mobile-menu-button" onClick={()=>setMobileOpen(!mobileOpen)}><Menu size={20}/></button><div className="crumb">Perpustakaan <ChevronRight size={14}/><b>{nav.find(n=>n.id===view)?.label}</b></div><div className="top-actions"><div className="user-chip"><div className="avatar">{user.name[0]}</div><div><b>{user.name}</b><small>{user.role}</small></div></div></div></header><main className="main-area"><div className="page-heading"><div><p className="eyebrow">SMA 1 NEGERI ABUNG TENGAH · {new Date().toLocaleDateString("id-ID",{day:"numeric",month:"long",year:"numeric"})}</p><h2>{view==="overview"?`Selamat datang, ${user.name.split(" ")[0]}.`:nav.find(n=>n.id===view)?.label}</h2></div>{view==="overview"&&<button className="primary" data-testid="quick-circulation-button" onClick={()=>setView("circulation")}><ScanLine size={17}/> Mulai sirkulasi</button>}</div>{view==="overview"&&<Overview data={data} onNavigate={setView}/>} {view==="books"&&<Books data={data} reload={load} notify={notify}/>} {view==="members"&&<Members data={data} reload={load} notify={notify}/>} {view==="shelves"&&<Shelves data={data}/>} {view==="circulation"&&<Circulation data={data} reload={load} notify={notify}/>} {view==="reports"&&<Reports data={data}/>}</main></div>{toast&&<div className="toast" data-testid="toast-message">{toast}</div>}</div>
}

function Overview({data,onNavigate}) { const s=data.stats; return <><section className="welcome-banner"><div><p className="eyebrow light">PUSAT KENDALI HARI INI</p><h1>Pengetahuan yang terkelola,<br/>sekolah yang <em>bertumbuh.</em></h1><p>Kelola koleksi, pantau aktivitas, dan bantu siswa menemukan buku terbaik.</p><button className="banner-button" data-testid="banner-circulation-button" onClick={()=>onNavigate("circulation")}>Buka sirkulasi <ChevronRight size={16}/></button></div><div className="banner-art"><BookOpen size={88}/><div className="art-line line-one"/><div className="art-line line-two"/></div></section><section className="stat-grid">{[["Total koleksi",s.books,"buku",BookOpen,"blue"],["Anggota aktif",s.members,"siswa & guru",Users,"green"],["Sedang dipinjam",s.borrowed,"perlu dipantau",ClipboardList,"orange"],["Buku hilang",s.missing,"dari koleksi",Boxes,"red"]].map(([label,value,sub,Icon,color])=><div className="stat-card" key={label} data-testid={`stat-${label.replaceAll(" ","-").toLowerCase()}`}><div className={`stat-icon ${color}`}><Icon size={19}/></div><span>{label}</span><strong>{fmt(value)}</strong><small>{sub}</small></div>)}</section><div className="section-row"><div className="panel activity-panel"><div className="panel-title"><div><p className="eyebrow">AKTIVITAS TERBARU</p><h3>Transaksi terakhir</h3></div><button className="text-button" data-testid="view-all-transactions-button" onClick={()=>onNavigate("reports")}>Lihat semua <ChevronRight size={15}/></button></div>{data.transactions.slice(0,4).map(t=><div className="activity" key={t.id}><div className={`activity-icon ${t.action==="pinjam"?"borrow":"return"}`}>{t.action==="pinjam"?<BookOpen size={16}/>:<ClipboardList size={16}/>}</div><div><b>{t.member_name}</b><span>{t.action==="pinjam"?"meminjam":"mengembalikan"} “{t.book_title}”</span></div><time>{new Date(t.date).toLocaleDateString("id-ID",{day:"numeric",month:"short"})}</time></div>)}</div><div className="panel shortcut-panel"><div className="panel-title"><div><p className="eyebrow">AKSES CEPAT</p><h3>Yang ingin Anda lakukan?</h3></div></div><button className="shortcut" data-testid="shortcut-add-book-button" onClick={()=>onNavigate("books")}><span className="shortcut-icon"><Plus size={18}/></span><div><b>Tambah buku baru</b><small>Perbarui koleksi perpustakaan</small></div><ChevronRight size={16}/></button><button className="shortcut" data-testid="shortcut-add-member-button" onClick={()=>onNavigate("members")}><span className="shortcut-icon green"><Users size={18}/></span><div><b>Daftarkan anggota</b><small>Buat kartu anggota digital</small></div><ChevronRight size={16}/></button><button className="shortcut" data-testid="shortcut-shelves-button" onClick={()=>onNavigate("shelves")}><span className="shortcut-icon orange"><Boxes size={18}/></span><div><b>Susunan rak</b><small>Lihat tata letak koleksi</small></div><ChevronRight size={16}/></button></div></div></>
}

function PhotoBox({ value, onChange, label = "Foto", testId }) {
  const inputRef = useRef(null);
  const pick = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    try { const data = await readFile(file); onChange(data); } catch (err) { alert(err.message); }
  };
  return <div className="photo-box" data-testid={testId}>
    <div className="photo-preview">{value ? <img src={value} alt={label}/> : <Camera size={28}/>}</div>
    <div className="photo-actions">
      <button type="button" className="secondary" data-testid={`${testId}-upload-button`} onClick={()=>inputRef.current?.click()}><Upload size={14}/> Unggah {label.toLowerCase()}</button>
      {value && <button type="button" className="text-button" data-testid={`${testId}-remove-button`} onClick={()=>onChange("")}>Hapus</button>}
      <small>JPG/PNG, maks 900KB</small>
      <input ref={inputRef} type="file" accept="image/*" hidden onChange={pick} data-testid={`${testId}-input`}/>
    </div>
  </div>;
}

function Books({data,reload,notify}) {
  const [search,setSearch]=useState(""); const [show,setShow]=useState(false);
  const emptyForm = {title:"",author:"",category:"Umum",shelf:"R-01",isbn:"",cover:""};
  const [form,setForm]=useState(emptyForm);
  const filtered=data.books.filter(b=>`${b.title} ${b.author} ${b.category}`.toLowerCase().includes(search.toLowerCase()));
  const add=async(e)=>{e.preventDefault();await api.post("/books",form);setShow(false);setForm(emptyForm);reload();notify("Buku berhasil ditambahkan")};
  const remove=async(id)=>{if(window.confirm("Hapus buku ini dari koleksi?")){await api.delete(`/books/${id}`);reload();notify("Buku dihapus")}};
  return <><div className="toolbar"><div className="searchbox"><Search size={17}/><input data-testid="book-search-input" placeholder="Cari judul, penulis, atau kategori..." value={search} onChange={e=>setSearch(e.target.value)}/></div><button className="primary" data-testid="add-book-button" onClick={()=>setShow(true)}><Plus size={17}/> Tambah buku</button></div><div className="panel table-panel"><div className="panel-title"><div><p className="eyebrow">INVENTARIS KOLEKSI</p><h3>{filtered.length} buku dalam katalog</h3></div><span className="soft-badge"><Boxes size={14}/> {data.shelves.length} rak aktif</span></div><div className="table-wrap"><table><thead><tr><th>BUKU</th><th>KATEGORI</th><th>RAK</th><th>STATUS</th><th></th></tr></thead><tbody>{filtered.map(b=><tr key={b.id}><td><div className="book-cell"><div className="book-cover">{b.cover?<img src={b.cover} alt={b.title}/>:<BookOpen size={18}/>}</div><div><b>{b.title}</b><span>{b.author} · {b.id}</span></div></div></td><td>{b.category}</td><td><span className="shelf-tag">{b.shelf}</span></td><td><span className={`status ${b.status.toLowerCase()}`}>{b.status}</span></td><td><button className="danger-icon" data-testid={`delete-book-${b.id}-button`} onClick={()=>remove(b.id)}><Trash2 size={16}/></button></td></tr>)}</tbody></table></div></div>{show&&<Modal title="Tambah buku baru" close={()=>setShow(false)}><form onSubmit={add} className="modal-form"><PhotoBox value={form.cover} onChange={(v)=>setForm({...form,cover:v})} label="Sampul buku" testId="book-cover-box"/>{[["title","Judul buku"],["author","Penulis"],["isbn","ISBN (opsional)"]].map(([key,label])=><label key={key}>{label}<input data-testid={`book-${key}-input`} required={key!=="isbn"} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/></label>)}<label>Kategori<select data-testid="book-category-input" value={form.category} onChange={e=>setForm({...form,category:e.target.value})}><option>Umum</option><option>Sastra</option><option>Sains</option><option>Pelajaran</option></select></label><label>Rak<select data-testid="book-shelf-input" value={form.shelf} onChange={e=>setForm({...form,shelf:e.target.value})}>{data.shelves.map(s=><option key={s.id}>{s.id}</option>)}</select></label><button className="primary full" data-testid="save-book-button">Simpan buku</button></form></Modal>}</>
}

function Members({data,reload,notify}) {
  const [show,setShow]=useState(false); const [selected,setSelected]=useState(data.members[0]);
  useEffect(()=>{if(!selected && data.members[0])setSelected(data.members[0])},[data.members]);
  const emptyForm = {name:"",student_id:"",class_name:"",email:"",phone:"",photo:""};
  const [form,setForm]=useState(emptyForm);
  const add=async(e)=>{e.preventDefault();await api.post("/members",form);setShow(false);setForm(emptyForm);reload();notify("Anggota berhasil ditambahkan")};
  return <><div className="toolbar"><div><p className="eyebrow">DIREKTORI SEKOLAH</p><h3 className="toolbar-title">{data.members.length} anggota terdaftar</h3></div><button className="primary" data-testid="add-member-button" onClick={()=>setShow(true)}><Plus size={17}/> Tambah anggota</button></div><div className="member-layout"><div className="panel member-list"><div className="panel-title"><h3>Daftar anggota</h3></div>{data.members.map(m=><button className={selected?.id===m.id?"member-row selected":"member-row"} data-testid={`member-${m.id}-button`} key={m.id} onClick={()=>setSelected(m)}><div className="avatar large">{m.photo?<img src={m.photo} alt={m.name}/>:m.name[0]}</div><div><b>{m.name}</b><span>{m.student_id} · {m.class_name}</span></div><ChevronRight size={16}/></button>)}</div><div className="member-card-wrap"><p className="eyebrow">PRATINJAU KARTU DIGITAL</p><MemberCard member={selected}/><button className="secondary print-btn" data-testid="print-member-card-button" onClick={()=>window.print()}><CreditCard size={17}/> Cetak kartu anggota</button></div></div>{show&&<Modal title="Daftarkan anggota baru" close={()=>setShow(false)}><form onSubmit={add} className="modal-form"><PhotoBox value={form.photo} onChange={(v)=>setForm({...form,photo:v})} label="Foto anggota" testId="member-photo-box"/>{[["name","Nama lengkap"],["student_id","NIS"],["class_name","Kelas"],["email","Email"],["phone","Nomor telepon"]].map(([key,label])=><label key={key}>{label}<input data-testid={`member-${key}-input`} required={key!=="email"&&key!=="phone"} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/></label>)}<button className="primary full" data-testid="save-member-button">Simpan anggota</button></form></Modal>}</>
}

function MemberCard({member}) {
  if(!member)return null;
  const qrSrc = `https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(member.id)}&margin=0&color=0f2745&bgcolor=ffffff`;
  return <div className="id-card" id="print-card" data-testid="digital-member-card"><div className="id-card-top"><div className="mini-logo"><BookOpen size={17}/></div><div><b>SMA 1 NEGERI ABUNG TENGAH</b><small>KARTU ANGGOTA PERPUSTAKAAN</small></div><img className="id-qr" src={qrSrc} alt={`QR ${member.id}`}/></div><div className="id-card-body"><div className="photo">{member.photo?<img src={member.photo} alt={member.name}/>:member.name[0]}</div><div><span>PEMILIK KARTU</span><h3>{member.name}</h3><p>{member.class_name} · NIS {member.student_id}</p><p>{member.email || "Anggota aktif"}</p></div></div><div className="id-card-foot"><span>Jln Raya Subik, Pekurun Selatan</span><b>{member.id}</b></div></div>
}

function Shelves({data}) {
  return <div className="shelves-grid">{data.shelves.map(s=>{const books=data.books.filter(b=>b.shelf===s.id);const occ=Math.round((books.length/(s.capacity||1))*100);return <div className="shelf-card" key={s.id} data-testid={`shelf-${s.id}`}><div className="shelf-head"><div><p className="eyebrow">RAK {s.id}</p><h3>{s.name}</h3></div><span className="shelf-tag">{books.length}/{s.capacity}</span></div><div className="shelf-bar"><div style={{width:`${Math.min(occ,100)}%`}}/></div><small>{occ}% kapasitas</small><div className="shelf-books">{books.slice(0,6).map(b=><div className="shelf-spine" key={b.id} title={b.title}>{b.cover?<img src={b.cover} alt={b.title}/>:<BookOpen size={14}/>}<span>{b.title}</span></div>)}{books.length===0&&<p className="muted" style={{fontSize:12}}>Belum ada buku di rak ini</p>}</div></div>})}</div>
}

function QRScanner({ onDetect, onClose }) {
  const scannerRef = useRef(null);
  const [cams, setCams] = useState([]); const [camId, setCamId] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => {
    Html5Qrcode.getCameras().then(list => { setCams(list); if (list[0]) setCamId(list[0].id); }).catch(() => setErr("Kamera tidak tersedia. Gunakan input manual."));
    return () => { scannerRef.current?.stop().catch(()=>{}); scannerRef.current?.clear().catch(()=>{}); };
  }, []);
  useEffect(() => {
    if (!camId) return;
    const el = document.getElementById("qr-reader");
    if (!el) return;
    const scanner = new Html5Qrcode("qr-reader", { verbose: false });
    scannerRef.current = scanner;
    scanner.start(camId, { fps: 10, qrbox: { width: 220, height: 220 } }, (text) => { onDetect(text); scanner.stop().catch(()=>{}); }, () => {}).catch(e => setErr("Gagal mengakses kamera: " + e));
    return () => { scanner.stop().catch(()=>{}); };
  }, [camId]);
  return <Modal title="Pindai QR Code" close={onClose}>
    <div className="qr-shell" data-testid="qr-scanner">
      <div id="qr-reader" className="qr-reader"/>
      {err && <div className="error">{err}</div>}
      {cams.length > 1 && <label>Pilih kamera<select data-testid="qr-camera-select" value={camId} onChange={e=>setCamId(e.target.value)}>{cams.map(c=><option key={c.id} value={c.id}>{c.label||c.id}</option>)}</select></label>}
      <p className="muted" style={{fontSize:12}}>Arahkan QR Code anggota atau kode buku ke dalam kotak.</p>
    </div>
  </Modal>;
}

function Circulation({data,reload,notify}) {
  const [mode,setMode]=useState("pinjam"); const [member,setMember]=useState(""); const [book,setBook]=useState("");
  const [scan,setScan]=useState(false); const [scanTarget,setScanTarget]=useState("member");
  const [manual,setManual]=useState("");
  const choices=data.books.filter(b=>mode==="kembali"?b.status==="Dipinjam":b.status==="Tersedia");
  const resolveCode=(code)=>{const c=code.trim().toUpperCase();const m=data.members.find(x=>x.id.toUpperCase()===c||x.student_id?.toUpperCase()===c);const b=data.books.find(x=>x.id.toUpperCase()===c||x.isbn?.toUpperCase()===c);if(m){setMember(m.id);notify(`Anggota: ${m.name}`);return true}if(b){setBook(b.id);notify(`Buku: ${b.title}`);return true}notify("Kode tidak ditemukan");return false};
  const submit=async()=>{if(!member||!book)return notify("Pilih anggota dan buku terlebih dahulu");try{await api.post("/transactions",{member_id:member,book_id:book,action:mode});reload();notify(mode==="pinjam"?"Peminjaman tercatat":"Pengembalian tercatat");setMember("");setBook("")}catch(e){notify(e.response?.data?.detail||"Transaksi gagal")}};
  const openScanner=(t)=>{setScanTarget(t);setScan(true)};
  const applyManual=()=>{if(!manual.trim())return;resolveCode(manual);setManual("")};
  return <><div className="circulation-grid"><div className="panel circulation-panel"><div className="mode-switch"><button data-testid="borrow-mode-button" className={mode==="pinjam"?"selected":""} onClick={()=>setMode("pinjam")}>Pinjam buku</button><button data-testid="return-mode-button" className={mode==="kembali"?"selected":""} onClick={()=>setMode("kembali")}>Kembalikan</button></div>
    <div className="scanner-box"><ScanLine size={40}/><h3>Pindai QR anggota &amp; buku</h3><p>Bisa menggunakan kamera HP, atau input kode manual di bawah.</p><div className="scan-buttons"><button className="secondary" data-testid="scan-member-button" onClick={()=>openScanner("member")}><QrCode size={16}/> Scan Anggota</button><button className="secondary" data-testid="scan-book-button" onClick={()=>openScanner("book")}><QrCode size={16}/> Scan Buku</button></div></div>
    <div className="manual-row"><input placeholder="Ketik/tempel kode (MB-xxx atau BK-xxx)" value={manual} onChange={e=>setManual(e.target.value)} data-testid="manual-code-input" onKeyDown={e=>{if(e.key==="Enter"){e.preventDefault();applyManual()}}}/><button className="secondary" data-testid="apply-manual-code-button" onClick={applyManual}>Terapkan</button></div>
    <div className="or-line"><span>atau pilih dari daftar</span></div>
    <label>Anggota<select data-testid="circulation-member-select" value={member} onChange={e=>setMember(e.target.value)}><option value="">Pilih anggota</option>{data.members.map(m=><option key={m.id} value={m.id}>{m.name} · {m.student_id}</option>)}</select></label>
    <label>Buku<select data-testid="circulation-book-select" value={book} onChange={e=>setBook(e.target.value)}><option value="">Pilih buku</option>{choices.map(b=><option key={b.id} value={b.id}>{b.title} · {b.id}</option>)}</select></label>
    <button className="primary full" data-testid="submit-circulation-button" onClick={submit}>{mode==="pinjam"?"Catat peminjaman":"Catat pengembalian"} <ChevronRight size={17}/></button></div>
    <div className="panel today-panel"><div className="panel-title"><div><p className="eyebrow">HARI INI</p><h3>Aktivitas sirkulasi</h3></div><span className="live-dot">LIVE</span></div>{data.transactions.slice(0,7).map(t=><div className="mini-transaction" key={t.id}><div className={`activity-icon ${t.action==="pinjam"?"borrow":"return"}`}>{t.action==="pinjam"?<BookOpen size={15}/>:<ClipboardList size={15}/>}</div><div><b>{t.member_name}</b><span>{t.book_title}</span></div><small>{t.action}</small></div>)}<div className="zero-fine"><ShieldCheck size={17}/><span><b>Tidak ada denda anggota</b><small>Fokus pada budaya membaca, bukan sanksi.</small></span></div></div>
  </div>
  {scan && <QRScanner onDetect={(code)=>{setScan(false);resolveCode(code)}} onClose={()=>setScan(false)}/>}</>
}

function Reports({data}) {
  const [tab,setTab]=useState("transaksi"); const [period,setPeriod]=useState("semua"); const reportData=data.reports||{incoming:[],missing:[]};
  const now=new Date();
  const inPeriod=(d)=>{const dt=new Date(d);if(period==="harian")return dt.toDateString()===now.toDateString();if(period==="bulanan")return dt.getMonth()===now.getMonth()&&dt.getFullYear()===now.getFullYear();return true};
  const txs=data.transactions.filter(t=>inPeriod(t.date));
  const rows=tab==="transaksi"?txs:tab==="masuk"?reportData.incoming:reportData.missing;
  return <><div className="report-tabs"><button data-testid="report-transactions-tab" className={tab==="transaksi"?"active":""} onClick={()=>setTab("transaksi")}>Transaksi</button><button data-testid="report-incoming-tab" className={tab==="masuk"?"active":""} onClick={()=>setTab("masuk")}>Buku masuk</button><button data-testid="report-missing-tab" className={tab==="hilang"?"active":""} onClick={()=>setTab("hilang")}>Buku hilang</button>{tab==="transaksi"&&<div className="period-select"><button data-testid="period-all" className={period==="semua"?"active":""} onClick={()=>setPeriod("semua")}>Semua</button><button data-testid="period-daily" className={period==="harian"?"active":""} onClick={()=>setPeriod("harian")}>Harian</button><button data-testid="period-monthly" className={period==="bulanan"?"active":""} onClick={()=>setPeriod("bulanan")}>Bulanan</button></div>}</div>
  <div className="report-summary"><div><span>Total transaksi</span><b>{txs.length}</b><small>{period==="harian"?"Hari ini":period==="bulanan"?"Bulan ini":"Semua waktu"}</small></div><div><span>Peminjaman</span><b>{txs.filter(t=>t.action==="pinjam").length}</b><small>Perlu dikembalikan</small></div><div><span>Pengembalian</span><b>{txs.filter(t=>t.action==="kembali").length}</b><small>Buku kembali</small></div></div>
  <div className="panel table-panel"><div className="panel-title"><div><p className="eyebrow">LAPORAN {tab.toUpperCase()}</p><h3>{tab==="transaksi"?"Riwayat transaksi":tab==="masuk"?"Penerimaan koleksi baru":"Daftar buku hilang"}</h3></div><button className="secondary" data-testid="print-report-button" onClick={()=>window.print()}>Cetak laporan</button></div>
  <div className="table-wrap"><table><thead><tr><th>{tab==="transaksi"?"ANGGOTA":"JUDUL BUKU"}</th><th>{tab==="transaksi"?"BUKU":"KETERANGAN"}</th><th>TANGGAL</th><th>STATUS</th></tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td><b>{tab==="transaksi"?r.member_name:r.title}</b></td><td>{tab==="transaksi"?r.book_title:r.detail}</td><td>{tab==="transaksi"?new Date(r.date).toLocaleDateString("id-ID"):r.date}</td><td><span className={`status ${tab==="transaksi"?"tersedia":tab==="masuk"?"tersedia":"hilang"}`}>{tab==="transaksi"?r.action:r.status}</span></td></tr>)}{rows.length===0&&<tr><td colSpan={4} style={{textAlign:"center",padding:30,color:"#94a3b8"}}>Belum ada data pada periode ini</td></tr>}</tbody></table></div></div></>
}

function Modal({title,close,children}) { return <div className="modal-backdrop" data-testid="modal-backdrop" onClick={(e)=>{if(e.target.classList.contains("modal-backdrop"))close()}}><div className="modal"><div className="modal-head"><h3>{title}</h3><button className="icon-button" data-testid="close-modal-button" onClick={close}><X size={18}/></button></div>{children}</div></div> }

export default App;
