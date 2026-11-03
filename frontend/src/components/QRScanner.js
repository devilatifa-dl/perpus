import { lazy, Suspense, useState } from "react";
import { Modal } from "./Shared";

// Pustaka kamera/QR cukup besar: baru diunduh saat pemindai dibuka
const CameraScanner = lazy(() => import("./CameraScanner").then((m) => ({ default: m.CameraScanner })));

export function QRScanner({ onDetect, onClose }) {
  const [manual, setManual] = useState("");
  const submit = (e) => { e.preventDefault(); if (manual.trim()) onDetect(manual.trim()); };
  return <Modal title="Pindai QR Code" close={onClose}>
    <div className="qr-shell" data-testid="qr-scanner">
      <Suspense fallback={<div className="cam-lazy" data-testid="qr-camera-loading">Menyiapkan kamera...</div>}><CameraScanner onCode={onDetect} testId="qr-camera"/></Suspense>
      <p className="muted" style={{ fontSize: 12 }}>Arahkan QR Code anggota atau kode buku ke dalam kotak.</p>
      <form className="manual-row" onSubmit={submit}>
        <input data-testid="qr-manual-input" placeholder="Atau ketik kode (MB-xxx / BK-xxx / NIS)" value={manual} onChange={(e) => setManual(e.target.value)}/>
        <button className="secondary" data-testid="qr-manual-submit">Pakai</button>
      </form>
    </div>
  </Modal>;
}
