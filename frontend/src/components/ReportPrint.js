import { Printer } from "lucide-react";

const PAGE_CSS = "@page{size:A4 portrait;margin:12mm 12mm 14mm}";

export function printReport() {
  const html = document.documentElement;
  const theme = html.getAttribute("data-theme");
  const style = document.createElement("style");
  style.textContent = PAGE_CSS;
  document.head.appendChild(style);
  document.body.classList.add("report-print");
  if (theme === "dark") html.setAttribute("data-theme", "light");
  const done = () => {
    document.body.classList.remove("report-print");
    style.remove();
    if (theme === "dark") html.setAttribute("data-theme", "dark");
    window.removeEventListener("afterprint", done);
  };
  window.addEventListener("afterprint", done);
  setTimeout(() => window.print(), 150);
}

export function PrintButton() {
  return <button type="button" className="primary report-print-btn" data-testid="print-report-button" onClick={printReport}><Printer size={16}/> Cetak</button>;
}

export function PrintSignature({ date }) {
  return <div className="print-sign" data-testid="print-signature">
    <div><span>Abung Tengah, {date}</span><span>Kepala Perpustakaan</span><b>( ................................ )</b></div>
  </div>;
}
