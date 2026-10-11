import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { Modal } from "./Shared";

export function QRScanner({ onDetect, onClose }) {
  const scannerRef = useRef(null);
  const [cams, setCams] = useState([]); const [camId, setCamId] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => {
    Html5Qrcode.getCameras().then(list => { setCams(list); if (list[0]) setCamId(list[0].id); }).catch(() => setErr("Kamera tidak tersedia. Gunakan input manual."));
    return () => { scannerRef.current?.stop().catch(()=>{}); scannerRef.current?.clear().catch(()=>{}); };
  }, []);
  useEffect(() => {
    if (!camId) return;
    const el = document.getElementById("qr-reader");
    if (!el) return;
    const scanner = new Html5Qrcode("qr-reader", { verbose: false });
    scannerRef.current = scanner;
    scanner.start(camId, { fps: 10, qrbox: { width: 220, height: 220 } }, (text) => { onDetect(text); scanner.stop().catch(()=>{}); }, () => {}).catch(e => setErr("Gagal mengakses kamera: " + e));
    return () => { scanner.stop().catch(()=>{}); };
  }, [camId]);
  return <Modal title="Pindai QR Code" close={onClose}>
    <div className="qr-shell" data-testid="qr-scanner">
      <div id="qr-reader" className="qr-reader"/>
      {err && <div className="error">{err}</div>}
      {cams.length > 1 && <label>Pilih kamera<select data-testid="qr-camera-select" value={camId} onChange={e=>setCamId(e.target.value)}>{cams.map(c=><option key={c.id} value={c.id}>{c.label||c.id}</option>)}</select></label>}
      <p className="muted" style={{fontSize:12}}>Arahkan QR Code anggota atau kode buku ke dalam kotak.</p>
    </div>
  </Modal>;
}
