import { Link } from "react-router-dom";
import { ChevronRight, GraduationCap, ShieldCheck } from "lucide-react";
import { LIBRARY_LOGO, SCHOOL_LOGO } from "../lib";
import { ThemeToggle } from "./ThemeToggle";

export default function PortalChooser() {
  return <main className="chooser" data-testid="portal-chooser">
    <ThemeToggle variant="floating" testId="chooser-theme-toggle"/>
    <div className="chooser-head"><img src={SCHOOL_LOGO} alt="Logo sekolah"/><img src={LIBRARY_LOGO} alt="Logo perpustakaan"/><p className="overline">PERPUSTAKAAN SMA NEGERI 1 ABUNG TENGAH</p><h1>Pilih pintu <em>masukmu.</em></h1><p className="login-copy">Dua alamat berbeda untuk dua peran berbeda. Petugas mengelola, siswa menjelajah.</p></div>
    <div className="chooser-grid">
      <Link to="/admin" className="chooser-card" data-testid="chooser-admin-link"><span className="chooser-icon"><ShieldCheck size={26}/></span><p className="eyebrow">ADMIN & PETUGAS</p><h2>/admin</h2><p>Kelola koleksi, anggota, sirkulasi QR, dan laporan.</p><b>Masuk <ChevronRight size={15}/></b></Link>
      <Link to="/siswa" className="chooser-card student" data-testid="chooser-student-link"><span className="chooser-icon"><GraduationCap size={26}/></span><p className="eyebrow">SISWA</p><h2>/siswa</h2><p>Hanya melihat katalog buku dan susunan rak.</p><b>Masuk <ChevronRight size={15}/></b></Link>
    </div>
    <p className="chooser-foot">Jln Raya Subik, Desa Pekurun Selatan</p>
  </main>;
}
