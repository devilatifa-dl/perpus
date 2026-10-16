import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Printer, X } from "lucide-react";
import { MemberCard } from "./MemberCard";
import { MemberCardBack } from "./MemberCardBack";

function Sheet({ cards, back, portrait, settings, page }) {
  return <div className={`print-sheet ${portrait ? "portrait" : ""} ${back ? "back-side" : ""} ${page ? "duplex-page" : ""}`} data-testid={page ? `duplex-sheet-${page}-${back ? "back" : "front"}` : "print-sheet"}>
    {page && <span className="sheet-label">Halaman {page} · {back ? "Belakang" : "Depan"}</span>}
    {cards.map((m) => <div className="print-slot" key={m.id} data-testid={back ? `bulk-card-back-${m.id}` : `bulk-card-${m.id}`}>{back ? <MemberCardBack settings={settings} testId={`card-back-${m.id}`}/> : <MemberCard member={m} settings={settings}/>}</div>)}
  </div>;
}

export function BulkCardPrint({ members, settings, close }) {
  const classes = useMemo(() => [...new Set(members.map((m) => m.class_name))].sort(), [members]);
  const [klass, setKlass] = useState("semua"); const [side, setSide] = useState("depan");
  const list = members.filter((m) => klass === "semua" || m.class_name === klass);
  const portrait = settings?.card_layout === "portrait";
  const perPage = portrait ? 9 : 10;
  const pages = Math.ceil(list.length / perPage) || 0;
  const chunks = Array.from({ length: pages }, (_, i) => list.slice(i * perPage, (i + 1) * perPage));
  useEffect(() => { document.body.classList.add("bulk-mode"); return () => document.body.classList.remove("bulk-mode"); }, []);
  const duplex = side === "dua";
  return createPortal(<div className="bulk-print" data-testid="bulk-print-view">
    <div className="bulk-toolbar">
      <div><p className="eyebrow">CETAK MASSAL KARTU ANGGOTA</p><h3>{list.length} kartu · {duplex ? `${pages * 2} halaman A4 (${pages} lembar bolak-balik)` : `${pages} halaman A4`} · ukuran ID 8,6 × 5,6 cm (86 × 56 mm)</h3></div>
      <div className="bulk-actions">
        <label>Kelas<select data-testid="bulk-class-select" value={klass} onChange={(e) => setKlass(e.target.value)}><option value="semua">Semua kelas</option>{classes.map((c) => <option key={c} value={c}>{c}</option>)}</select></label>
        <label>Sisi<select data-testid="bulk-side-select" value={side} onChange={(e) => setSide(e.target.value)}><option value="depan">Depan (data anggota)</option><option value="belakang">Belakang (peraturan)</option><option value="dua">Dua sisi (bolak-balik)</option></select></label>
        <button className="primary" data-testid="bulk-print-button" onClick={() => window.print()} disabled={!list.length}><Printer size={16}/> {duplex ? `Cetak dua sisi (${pages * 2} halaman)` : `Cetak ${list.length} kartu`}</button>
        <button className="icon-button" data-testid="bulk-close-button" onClick={close}><X size={18}/></button>
      </div>
    </div>
    {side === "belakang" && <p className="bulk-hint" data-testid="bulk-back-hint">Urutan kolom dicerminkan agar pas saat dicetak bolak-balik (cetak sisi depan dulu, lalu balik kertasnya).</p>}
    {duplex && <p className="bulk-hint" data-testid="bulk-duplex-hint">Halaman depan dan belakang disusun bergantian (1 depan, 1 belakang, 2 depan, …). Di dialog cetak pilih <b>Cetak dua sisi → Balik pada sisi panjang (long edge)</b>, ukuran A4, skala 100%, margin tidak ada.</p>}
    {duplex ? <div data-testid="duplex-sheets">{chunks.map((c, i) => <div key={i}><Sheet cards={c} portrait={portrait} settings={settings} page={i + 1}/><Sheet cards={c} back portrait={portrait} settings={settings} page={i + 1}/></div>)}</div>
      : <Sheet cards={list} back={side === "belakang"} portrait={portrait} settings={settings}/>}
    {list.length === 0 && <p className="muted" style={{ textAlign: "center" }}>Tidak ada anggota di kelas ini.</p>}
  </div>, document.body);
}
