import { DEFAULT_SETTINGS, LIBRARY_LOGO, SCHOOL_LOGO } from "../lib";

export function MemberCard({ member, settings }) {
  if (!member) return null;
  const s = { ...DEFAULT_SETTINGS, ...(settings || {}) };
  const qrSrc = `https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(member.id)}&margin=0&color=0f2745&bgcolor=ffffff`;
  const qr = s.card_show_qr && <div className="id-qr-wrap"><img className="id-qr" src={qrSrc} alt={`QR ${member.id}`}/></div>;
  return <div className={`id-card theme-${s.card_theme} layout-${s.card_layout}`} id="print-card" data-testid="digital-member-card">
    <div className="id-card-top">
      <div className="card-logos"><img className="card-logo" src={s.school_logo || SCHOOL_LOGO} alt="Logo sekolah" data-testid="card-school-logo"/><img className="card-logo" src={s.library_logo || LIBRARY_LOGO} alt="Logo perpustakaan" data-testid="card-library-logo"/></div>
      <div className="card-school"><b>SMA 1 NEGERI ABUNG TENGAH</b><small data-testid="card-title-text">{s.card_title}</small></div>
      {s.card_layout === "classic" && qr}
    </div>
    <div className="id-card-body">
      <div className="photo">{member.photo ? <img src={member.photo} alt={member.name}/> : member.name[0]}</div>
      <div className="card-identity"><span>PEMILIK KARTU</span><h3>{member.name}</h3><p>{member.class_name} · NIS {member.student_id}</p><p>Anggota aktif · Tanpa denda</p></div>
      {s.card_layout !== "classic" && qr}
    </div>
    <div className="id-card-foot">{s.card_show_address && <span>Jln Raya Subik, Desa Pekurun Selatan</span>}<b>{member.id}</b></div>
  </div>;
}
