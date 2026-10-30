import { useMemo, useState } from "react";
import { CameraOff, CheckCircle2, ChevronDown, Search, Users } from "lucide-react";

const NO_CLASS = "(Tanpa kelas)";
const hasPhoto = (m) => !!(m.photo && String(m.photo).trim());

export function MemberClassList({ members, renderRow }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(() => new Set());
  const [onlyNoPhoto, setOnlyNoPhoto] = useState(false);
  const missingTotal = useMemo(() => members.filter((m) => !hasPhoto(m)).length, [members]);
  const groups = useMemo(() => {
    const t = q.trim().toLowerCase();
    const map = {};
    members.forEach((m) => {
      if (t && ![m.name, m.student_id, m.class_name].some((v) => (v || "").toLowerCase().includes(t))) return;
      if (onlyNoPhoto && hasPhoto(m)) return;
      (map[m.class_name || NO_CLASS] ||= []).push(m);
    });
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0], "id", { numeric: true }))
      .map(([cls, list]) => [cls, list.sort((a, b) => (hasPhoto(a) - hasPhoto(b)) || a.name.localeCompare(b.name, "id"))]);
  }, [members, q, onlyNoPhoto]);
  // Hitungan "belum foto" per kelas selalu dari seluruh anggota kelas (tidak terpengaruh filter)
  const missingByClass = useMemo(() => {
    const map = {};
    members.forEach((m) => { const c = m.class_name || NO_CLASS; map[c] ||= { total: 0, missing: 0 }; map[c].total += 1; if (!hasPhoto(m)) map[c].missing += 1; });
    return map;
  }, [members]);
  const toggle = (cls) => setOpen((s) => { const n = new Set(s); n.has(cls) ? n.delete(cls) : n.add(cls); return n; });
  const searching = q.trim() !== "" || onlyNoPhoto;

  return <div className="class-list" data-testid="member-class-list">
    <div className="searchbox class-search"><Search size={16}/><input data-testid="member-list-search" placeholder="Cari nama atau NIS..." value={q} onChange={(e) => setQ(e.target.value)}/></div>
    <div className="photo-filter" role="radiogroup" aria-label="Saring foto anggota" data-testid="member-photo-filter">
      <button type="button" role="radio" aria-checked={!onlyNoPhoto} className={!onlyNoPhoto ? "active" : ""} data-testid="member-photo-filter-all" onClick={() => setOnlyNoPhoto(false)}>Semua anggota</button>
      <button type="button" role="radio" aria-checked={onlyNoPhoto} className={`warn${onlyNoPhoto ? " active" : ""}`} data-testid="member-photo-filter-missing" onClick={() => setOnlyNoPhoto(true)} disabled={missingTotal === 0}><CameraOff size={13}/> Belum foto <b data-testid="member-photo-missing-total">{missingTotal}</b></button>
    </div>
    <p className="class-summary" data-testid="member-class-summary">{groups.length} kelas · {groups.reduce((a, g) => a + g[1].length, 0)} anggota{missingTotal > 0 ? <> · <span className="no-photo-text">{missingTotal} belum upload foto</span></> : <> · <span className="photo-done-text">semua sudah berfoto</span></>}</p>
    {groups.length === 0 && <p className="muted class-empty">{onlyNoPhoto ? "Semua anggota sudah punya foto." : "Anggota tidak ditemukan."}</p>}
    {groups.map(([cls, list]) => {
      const isOpen = searching || open.has(cls);
      const st = missingByClass[cls] || { total: list.length, missing: 0 };
      return <div className={`class-group${isOpen ? " open" : ""}`} key={cls} data-testid={`class-group-${cls}`}>
        <div className="class-head-row"><button type="button" className="class-head" data-testid={`class-toggle-${cls}`} onClick={() => toggle(cls)} aria-expanded={isOpen}>
          <span className="class-icon"><Users size={15}/></span>
          <span className="class-name"><small>Kelas</small><b>{cls}</b></span>
          {st.missing > 0
            ? <span className="class-photo-badge missing" title={`${st.missing} dari ${st.total} anggota belum upload foto`} data-testid={`class-photo-missing-${cls}`}><CameraOff size={12}/> {st.missing} belum foto</span>
            : <span className="class-photo-badge done" title="Semua anggota kelas ini sudah punya foto" data-testid={`class-photo-done-${cls}`}><CheckCircle2 size={12}/> Foto lengkap</span>}
          <span className="class-count" data-testid={`class-count-${cls}`}>{list.length} anggota</span>
          <ChevronDown size={17} className="class-chevron"/>
        </button></div>
        {isOpen && <div className="class-body">{list.map(renderRow)}</div>}
      </div>;
    })}
  </div>;
}
