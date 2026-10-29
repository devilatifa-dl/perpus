import { useEffect, useState } from "react";
import { Printer, RectangleHorizontal, RectangleVertical } from "lucide-react";

// Orientasi kertas laporan (potret / lanskap). Dipakai untuk tombol Cetak, unduh PDF & Excel.
const KEY = "perpus-print-orientation";
const EVT = "perpus-print-orientation";
export const ORIENTATIONS = [["portrait", "Potret", RectangleVertical], ["landscape", "Lanskap", RectangleHorizontal]];

export function getPrintOrientation() {
  try { return localStorage.getItem(KEY) === "landscape" ? "landscape" : "portrait"; } catch { return "portrait"; }
}

export function setPrintOrientation(value) {
  const v = value === "landscape" ? "landscape" : "portrait";
  try { localStorage.setItem(KEY, v); } catch { /* storage penuh/ditolak: tetap pakai nilai di memori */ }
  window.dispatchEvent(new CustomEvent(EVT, { detail: v }));
}

export function usePrintOrientation() {
  const [value, setValue] = useState(getPrintOrientation);
  useEffect(() => {
    const on = (e) => setValue(e.detail || getPrintOrientation());
    window.addEventListener(EVT, on);
    return () => window.removeEventListener(EVT, on);
  }, []);
  return [value, setPrintOrientation];
}

export function printReport(orientation = getPrintOrientation()) {
  const html = document.documentElement;
  const theme = html.getAttribute("data-theme");
  const style = document.createElement("style");
  style.setAttribute("data-report-page", orientation);
  style.textContent = `@page{size:A4 ${orientation};margin:12mm 12mm 14mm}`;
  document.head.appendChild(style);
  document.body.classList.add("report-print", `print-${orientation}`);
  if (theme === "dark") html.setAttribute("data-theme", "light");
  const done = () => {
    document.body.classList.remove("report-print", "print-portrait", "print-landscape");
    style.remove();
    if (theme === "dark") html.setAttribute("data-theme", "dark");
    window.removeEventListener("afterprint", done);
  };
  window.addEventListener("afterprint", done);
  // Beri waktu grafik (ResponsiveContainer) menghitung ulang ukurannya selebar kertas sebelum dialog cetak terbuka.
  window.dispatchEvent(new Event("resize"));
  setTimeout(() => window.print(), 450);
}

export function OrientationToggle() {
  const [value, setValue] = usePrintOrientation();
  return <div className="print-orient" role="radiogroup" aria-label="Orientasi kertas" data-testid="print-orientation-toggle">
    {ORIENTATIONS.map(([k, label, Icon]) => <button key={k} type="button" role="radio" aria-checked={value === k} title={`Kertas ${label.toLowerCase()} (A4)`} data-testid={`print-orientation-${k}`} className={`po-btn${value === k ? " active" : ""}`} onClick={() => setValue(k)}><Icon size={15}/> {label}</button>)}
  </div>;
}

export function PrintButton() {
  const [orientation] = usePrintOrientation();
  return <>
    <OrientationToggle/>
    <button type="button" className="primary report-print-btn" data-testid="print-report-button" onClick={() => printReport(orientation)}><Printer size={16}/> Cetak</button>
  </>;
}

export function PrintSignature({ date }) {
  return <div className="print-sign" data-testid="print-signature">
    <div><span>Abung Tengah, {date}</span><span>Kepala Perpustakaan</span><b>( ................................ )</b></div>
  </div>;
}
