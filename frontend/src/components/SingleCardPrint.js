import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { MemberCard } from "./MemberCard";
import { MemberCardBack } from "./MemberCardBack";

// Cetak 1 kartu memakai lembar & slot yang SAMA dengan cetak massal (A4, kartu 86 × 56 mm,
// posisi = slot pertama), sehingga ukuran & tata letak hasil cetak identik.
export function SingleCardPrint({ member, settings, side = "depan", onDone }) {
  const ref = useRef(null);
  const portrait = settings?.card_layout === "portrait";
  useEffect(() => {
    let finished = false;
    const finish = () => { if (finished) return; finished = true; document.body.classList.remove("bulk-mode", "single-card-mode"); onDone?.(); };
    document.body.classList.add("bulk-mode", "single-card-mode");
    window.addEventListener("afterprint", finish);
    const start = setTimeout(async () => {
      const imgs = [...(ref.current?.querySelectorAll("img") || [])];
      await Promise.all(imgs.map((img) => (img.complete ? (img.decode ? img.decode().catch(() => {}) : null) : new Promise((r) => { img.onload = r; img.onerror = r; }))));
      if (document.fonts?.ready) await document.fonts.ready;
      window.print();
      setTimeout(finish, 1500); // cadangan bila browser tidak mengirim afterprint
    }, 120);
    return () => { clearTimeout(start); window.removeEventListener("afterprint", finish); document.body.classList.remove("bulk-mode", "single-card-mode"); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  if (!member) return null;
  return createPortal(<div className="bulk-print single-card-print" data-testid="single-card-print" ref={ref} aria-hidden="true">
    <div className={`print-sheet ${portrait ? "portrait" : ""}`} data-testid="single-print-sheet">
      <div className="print-slot" data-testid={side === "belakang" ? `single-card-back-${member.id}` : `single-card-${member.id}`}>
        {side === "belakang" ? <MemberCardBack settings={settings} testId="single-card-back"/> : <MemberCard member={member} settings={settings}/>}
      </div>
    </div>
  </div>, document.body);
}
