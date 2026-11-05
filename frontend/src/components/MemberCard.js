import { QRCodeSVG } from "qrcode.react";
import { DEFAULT_SETTINGS, LIBRARY_LOGO, SCHOOL_LOGO, cardFontClass, cardSizeVars } from "../lib";

export function MemberCard({ member, settings }) {
  if (!member) return null;
  const s = { ...DEFAULT_SETTINGS, ...(settings || {}) };
  const ff = (key) => cardFontClass(s, key);
  const qr = s.card_show_qr && <div className="id-qr-wrap"><QRCodeSVG className="id-qr" value={member.id} size={140} level="M" marginSize={0} fgColor="#0f2745" bgColor="#ffffff" title={`QR ${member.id}`} data-testid="member-card-qr"/></div>;
  const cls = `id-card fs-on theme-${s.card_theme} layout-${s.card_layout} font-${s.card_font} size-${s.card_font_size} photo-${s.card_photo_pos} shape-${s.card_photo_shape || "membulat"} qr-${s.card_qr_pos}`;
  const address = (s.card_address || "").trim();
  const showCode = s.card_show_code !== false;
  return <div className={cls} id="print-card" data-testid="digital-member-card" style={cardSizeVars(s)}>
    <div className="id-card-top">
      <img className="card-logo school-logo" style={{ order: s.card_school_logo_pos === "kanan" ? 5 : 0 }} src={s.school_logo || SCHOOL_LOGO} alt="Logo sekolah" data-testid="card-school-logo"/>
      <img className="card-logo library-logo" style={{ order: s.card_library_logo_pos === "kanan" ? 6 : 1 }} src={s.library_logo || LIBRARY_LOGO} alt="Logo perpustakaan" data-testid="card-library-logo"/>
      <div className="card-school" style={{ order: 3 }}><b className={ff("school").trim() || undefined} data-testid="card-school-name-text">{s.card_school_name}</b><small className={ff("title").trim() || undefined} data-testid="card-title-text">{s.card_title}</small></div>
      {s.card_qr_pos === "atas" && qr && <span className="qr-slot" style={{ order: 7 }}>{qr}</span>}
    </div>
    <div className="id-card-body">
      <div className="photo" data-testid="card-photo">{member.photo ? <img src={member.photo} alt={member.name}/> : member.name[0]}</div>
      <div className="card-identity">
        {s.card_owner_label && <span className={ff("owner").trim() || undefined} data-testid="card-owner-label">{s.card_owner_label}</span>}
        <h3 className={`${member.name.length > 20 ? "long-name" : ""}${ff("name")}`.trim() || undefined} data-testid="card-member-name">{member.name}</h3>
        {s.card_show_class !== false && <p className={`card-field card-field-class${ff("class")}`} data-testid="card-class"><i>{s.card_class_label}</i><em>:</em>{member.class_name}</p>}
        {s.card_show_nis !== false && <p className={`card-field card-field-nis${ff("nis")}`} data-testid="card-nis"><i>{s.card_nis_label}</i><em>:</em>{member.student_id}</p>}
      </div>
      {s.card_qr_pos === "bawah" && qr}
    </div>
    <div className="id-card-foot">{s.card_show_address && address && <span className={ff("address").trim() || undefined} data-testid="card-address-text">{address}</span>}{showCode && <b className={ff("code").trim() || undefined} data-testid="card-member-code">{member.id}</b>}</div>
  </div>;
}
