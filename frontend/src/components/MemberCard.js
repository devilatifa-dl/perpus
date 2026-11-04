import { QRCodeSVG } from "qrcode.react";
import { DEFAULT_SETTINGS, LIBRARY_LOGO, SCHOOL_LOGO, cardSizeVars } from "../lib";

export function MemberCard({ member, settings }) {
  if (!member) return null;
  const s = { ...DEFAULT_SETTINGS, ...(settings || {}) };
  const qr = s.card_show_qr && <div className="id-qr-wrap"><QRCodeSVG className="id-qr" value={member.id} size={140} level="M" marginSize={0} fgColor="#0f2745" bgColor="#ffffff" title={`QR ${member.id}`} data-testid="member-card-qr"/></div>;
  const cls = `id-card fs-on theme-${s.card_theme} layout-${s.card_layout} font-${s.card_font} size-${s.card_font_size} photo-${s.card_photo_pos} qr-${s.card_qr_pos}`;
  const address = (s.card_address || "").trim();
  return <div className={cls} id="print-card" data-testid="digital-member-card" style={cardSizeVars(s)}>
    <div className="id-card-top">
      <img className="card-logo school-logo" style={{ order: s.card_school_logo_pos === "kanan" ? 5 : 0 }} src={s.school_logo || SCHOOL_LOGO} alt="Logo sekolah" data-testid="card-school-logo"/>
      <img className="card-logo library-logo" style={{ order: s.card_library_logo_pos === "kanan" ? 6 : 1 }} src={s.library_logo || LIBRARY_LOGO} alt="Logo perpustakaan" data-testid="card-library-logo"/>
      <div className="card-school" style={{ order: 3 }}><b data-testid="card-school-name-text">{s.card_school_name}</b><small data-testid="card-title-text">{s.card_title}</small></div>
      {s.card_qr_pos === "atas" && qr && <span className="qr-slot" style={{ order: 7 }}>{qr}</span>}
    </div>
    <div className="id-card-body">
      <div className="photo">{member.photo ? <img src={member.photo} alt={member.name}/> : member.name[0]}</div>
      <div className="card-identity">{s.card_owner_label && <span data-testid="card-owner-label">{s.card_owner_label}</span>}<h3 className={member.name.length > 20 ? "long-name" : ""} data-testid="card-member-name">{member.name}</h3><p className="card-field" data-testid="card-class"><i>{s.card_class_label}</i><em>:</em>{member.class_name}</p><p className="card-field" data-testid="card-nis"><i>{s.card_nis_label}</i><em>:</em>{member.student_id}</p></div>
      {s.card_qr_pos === "bawah" && qr}
    </div>
    <div className="id-card-foot">{s.card_show_address && address && <span data-testid="card-address-text">{address}</span>}<b data-testid="card-member-code">{member.id}</b></div>
  </div>;
}
