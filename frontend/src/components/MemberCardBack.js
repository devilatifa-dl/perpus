import { DEFAULT_SETTINGS, LIBRARY_LOGO, SCHOOL_LOGO } from "../lib";

export function MemberCardBack({ settings, testId = "member-card-back" }) {
  const s = { ...DEFAULT_SETTINGS, ...(settings || {}) };
  const rules = (s.card_back_rules || "").split("\n").map((r) => r.trim()).filter(Boolean);
  return <div className={`id-card id-card-back theme-${s.card_theme} layout-${s.card_layout} font-${s.card_font} size-${s.card_font_size}`} data-testid={testId}>
    <div className="back-head">
      <img src={s.school_logo || SCHOOL_LOGO} alt="Logo sekolah"/>
      <b data-testid="card-back-title">{s.card_back_title}</b>
      <img src={s.library_logo || LIBRARY_LOGO} alt="Logo perpustakaan"/>
    </div>
    <ol className="back-rules" data-testid="card-back-rules">{rules.map((r, i) => <li key={i}>{r}</li>)}</ol>
    {s.card_back_web && <div className="back-web" data-testid="card-back-web">{s.card_back_web}</div>}
  </div>;
}
