import { Printer } from "lucide-react";

// Laporan selalu dicetak di kertas A4 potret.
export function printReport() {
  const html = document.documentElement;
  const theme = html.getAttribute("data-theme");
  const style = document.createElement("style");
  style.setAttribute("data-report-page", "portrait");
  style.textContent = "@page{size:A4 portrait;margin:12mm 12mm 14mm}";
  document.head.appendChild(style);
  document.body.classList.add("report-print", "print-portrait");
  if (theme === "dark") html.setAttribute("data-theme", "light");
  const done = () => {
    document.body.classList.remove("report-print", "print-portrait");
    style.remove();
    if (theme === "dark") html.setAttribute("data-theme", "dark");
    window.removeEventListener("afterprint", done);
  };
  window.addEventListener("afterprint", done);
  // Beri waktu grafik (ResponsiveContainer) menghitung ulang ukurannya selebar kertas sebelum dialog cetak terbuka.
  window.dispatchEvent(new Event("resize"));
  setTimeout(() => window.print(), 450);
}

export function PrintButton() {
  return <button type="button" className="primary report-print-btn" data-testid="print-report-button" onClick={printReport}><Printer size={16}/> Cetak</button>;
}

export function PrintSignature({ date }) {
  return <div className="print-sign" data-testid="print-signature">
    <div><span>Abung Tengah, {date}</span><span>Kepala Perpustakaan</span><b>( ................................ )</b></div>
  </div>;
}
