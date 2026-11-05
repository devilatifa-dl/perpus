import { useState } from "react";
import { ImageDown } from "lucide-react";
import { DEFAULT_DPI, DPI_OPTIONS, downloadCardPng, downloadCardsZip, safeName } from "../lib/cardExport";
import "../CardPrintHD.css";

/** Pilih DPI + tombol unduh. Mode tunggal: `getEl` mengembalikan elemen kartu. Mode massal: `getItems` mengembalikan [{el,name}]. */
export function CardHDButton({ getEl, member, getItems, zipName = "kartu-anggota.zip", notify, testId = "card-png-hd", label = "PNG HD", disabled }) {
  const [dpi, setDpi] = useState(DEFAULT_DPI); const [busy, setBusy] = useState("");
  const run = async () => {
    if (busy) return;
    try {
      if (getItems) {
        const items = getItems();
        if (!items.length) { notify?.("Tidak ada kartu untuk diunduh"); return; }
        setBusy(`0/${items.length}`);
        await downloadCardsZip(items, zipName.replace(/\.zip$/, `-${dpi}dpi.zip`), dpi, (i, n) => setBusy(`${i}/${n}`));
        notify?.(`${items.length} kartu PNG ${dpi} DPI berhasil diunduh (ZIP)`);
      } else {
        setBusy("…");
        const r = await downloadCardPng(getEl(), member, dpi);
        notify?.(`Kartu PNG ${dpi} DPI (${r.width}×${r.height} px) berhasil diunduh`);
      }
    } catch (e) {
      notify?.(e?.message ? `Gagal membuat PNG: ${e.message}` : "Gagal membuat PNG kartu");
    } finally { setBusy(""); }
  };
  return <span className="hd-export" data-testid={`${testId}-group`}>
    <select aria-label="Resolusi PNG" data-testid={`${testId}-dpi`} value={dpi} onChange={(e) => setDpi(Number(e.target.value))} disabled={!!busy}>{DPI_OPTIONS.map((d) => <option key={d} value={d}>{d} DPI</option>)}</select>
    <button type="button" className="secondary print-btn" data-testid={testId} onClick={run} disabled={disabled || !!busy}><ImageDown size={17}/> {busy ? `Menyiapkan ${busy === "…" ? "…" : busy}` : label}</button>
  </span>;
}

export { safeName };
