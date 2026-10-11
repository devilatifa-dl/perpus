import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { api, LIBRARY_LOGO, SCHOOL_LOGO } from "../lib";

const ACCOUNTS = { admin: ["admin@smansa.sch.id", "admin123"], petugas: ["petugas@smansa.sch.id", "petugas123"], siswa: ["siswa@smansa.sch.id", "siswa123"] };

export function Login({ onLogin, portal }) {
  const student = portal === "siswa";
  const roles = student ? ["siswa"] : ["admin", "petugas"];
  const [email, setEmail] = useState(ACCOUNTS[roles[0]][0]); const [password, setPassword] = useState(ACCOUNTS[roles[0]][1]); const [error, setError] = useState("");
  const submit = async (e) => { e.preventDefault(); try { const { data } = await api.post("/auth/login", { email, password, portal }); onLogin(data); } catch (err) { setError(err.response?.data?.detail || "Email atau kata sandi salah"); } };
  const demo = (role) => { setEmail(ACCOUNTS[role][0]); setPassword(ACCOUNTS[role][1]); setError(""); };
  return <main className={student ? "login-shell student" : "login-shell"} data-testid={`login-page-${portal}`}>
    <div className="login-visual">
      <div className="login-logos"><img src={SCHOOL_LOGO} alt="Logo SMA Negeri 1 Abung Tengah" data-testid="login-school-logo"/><img src={LIBRARY_LOGO} alt="Logo perpustakaan" data-testid="login-library-logo"/></div>
      <p className="overline">{student ? "PORTAL SISWA · PERPUSTAKAAN SEKOLAH" : "PORTAL PETUGAS & ADMIN · PERPUSTAKAAN SEKOLAH"}</p>
      <h1>{student ? <>Jelajahi koleksi,<br/><em>pinjam dengan mudah.</em></> : <>Temukan pengetahuan,<br/><em>mulai dari sini.</em></>}</h1>
      <p className="login-copy">{student ? "Lihat katalog buku dan susunan rak perpustakaan. Hanya lihat, tanpa mengubah data." : "Satu ruang digital untuk merawat koleksi, melayani siswa, dan menjaga budaya membaca."}</p>
      <div className="login-address"><span>SMA 1 NEGERI ABUNG TENGAH</span><span>Jln Raya Subik, Desa Pekurun Selatan</span></div>
    </div>
    <div className="login-panel"><div className="login-panel-inner">
      <p className="eyebrow">{student ? "HALO, SISWA" : "SELAMAT DATANG KEMBALI"}</p>
      <h2>{student ? "Masuk portal siswa" : "Masuk ke ruang kerja"}</h2>
      <p className="muted">{student ? "Akses baca-saja: katalog & rak buku." : "Khusus admin dan petugas perpustakaan."}</p>
      <form onSubmit={submit} data-testid="login-form">
        <label>Email sekolah<input data-testid="login-email-input" value={email} onChange={(e) => setEmail(e.target.value)} type="email" required/></label>
        <label>Kata sandi<input data-testid="login-password-input" value={password} onChange={(e) => setPassword(e.target.value)} type="password" required/></label>
        {error && <div className="error" data-testid="login-error">{error}</div>}
        <button className="primary full" data-testid="login-submit-button">{student ? "Masuk portal siswa" : "Masuk ke dashboard"} <ChevronRight size={17}/></button>
      </form>
      <div className="demo-login"><span>AKSES DEMO CEPAT</span><div>{roles.map((role) => <button key={role} data-testid={`demo-login-${role}-button`} onClick={() => demo(role)}>{role}</button>)}</div></div>
      <p className="portal-switch">{student ? <>Petugas atau admin? <Link to="/admin" data-testid="switch-to-admin-link">Masuk lewat /admin</Link></> : <>Kamu siswa? <Link to="/siswa" data-testid="switch-to-student-link">Masuk lewat /siswa</Link></>}</p>
    </div></div>
  </main>;
}
