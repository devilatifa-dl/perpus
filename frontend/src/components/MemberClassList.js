import { useMemo, useState } from "react";
import { ChevronDown, Printer, Search, Users } from "lucide-react";

const NO_CLASS = "(Tanpa kelas)";

export function MemberClassList({ members, renderRow, onPrintClass }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(() => new Set());
  const groups = useMemo(() => {
    const t = q.trim().toLowerCase();
    const map = {};
    members.forEach((m) => {
      if (t && ![m.name, m.student_id, m.class_name].some((v) => (v || "").toLowerCase().includes(t))) return;
      (map[m.class_name || NO_CLASS] ||= []).push(m);
    });
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0], "id", { numeric: true }))
      .map(([cls, list]) => [cls, list.sort((a, b) => a.name.localeCompare(b.name, "id"))]);
  }, [members, q]);
  const toggle = (cls) => setOpen((s) => { const n = new Set(s); n.has(cls) ? n.delete(cls) : n.add(cls); return n; });
  const searching = q.trim() !== "";

  return <div className="class-list" data-testid="member-class-list">
    <div className="searchbox class-search"><Search size={16}/><input data-testid="member-list-search" placeholder="Cari nama atau NIS..." value={q} onChange={(e) => setQ(e.target.value)}/></div>
    <p className="class-summary" data-testid="member-class-summary">{groups.length} kelas · {groups.reduce((a, g) => a + g[1].length, 0)} anggota</p>
    {groups.length === 0 && <p className="muted class-empty">Anggota tidak ditemukan.</p>}
    {groups.map(([cls, list]) => {
      const isOpen = searching || open.has(cls);
      return <div className={`class-group${isOpen ? " open" : ""}`} key={cls} data-testid={`class-group-${cls}`}>
        <div className="class-head-row"><button type="button" className="class-head" data-testid={`class-toggle-${cls}`} onClick={() => toggle(cls)} aria-expanded={isOpen}>
          <span className="class-icon"><Users size={15}/></span>
          <span className="class-name"><small>Kelas</small><b>{cls}</b></span>
          <span className="class-count" data-testid={`class-count-${cls}`}>{list.length} anggota</span>
          <ChevronDown size={17} className="class-chevron"/>
        </button>
        {onPrintClass && <button type="button" className="class-print" title={`Cetak kartu kelas ${cls}`} data-testid={`class-print-${cls}`} onClick={() => onPrintClass(cls === NO_CLASS ? "" : cls)}><Printer size={15}/><span>Cetak kartu</span></button>}</div>
        {isOpen && <div className="class-body">{list.map(renderRow)}</div>}
      </div>;
    })}
  </div>;
}
