import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { Modal } from "./Shared";
import { cameraError, createCamera } from "../lib/camera";

export function QRScanner({ onDetect, onClose }) {
  const [cams, setCams] = useState([]); const [camId, setCamId] = useState("");
  const [err, setErr] = useState("");
  const boxRef = useRef(null); const done = useRef(false); const cb = useRef(onDetect);
  cb.current = onDetect;
  useEffect(() => {
    setErr("");
    let alive = true; let cam = null;
    // Ditunda sedikit agar kamera hanya dibuka sekali (React dev memasang komponen dua kali)
    const t = setTimeout(() => {
      if (!alive || !boxRef.current) return;
      cam = createCamera(boxRef.current);
      cam.start((text) => {
        if (done.current) return;
        done.current = true;
        cam.stop();
        cb.current(text);
      }, camId || undefined).then(() => {
        if (alive) Html5Qrcode.getCameras().then((l) => alive && setCams(l)).catch(() => {});
      }).catch((e) => alive && setErr(cameraError(e)));
    }, 60);
    return () => { alive = false; clearTimeout(t); cam?.stop(); };
  }, [camId]);
  return <Modal title="Pindai QR Code" close={onClose}>
    <div className="qr-shell" data-testid="qr-scanner">
      <div ref={boxRef} id="qr-reader" className="qr-reader"/>
      {err && <div className="error" data-testid="qr-camera-error">{err}</div>}
      {cams.length > 1 && <label>Pilih kamera<select data-testid="qr-camera-select" value={camId} onChange={e=>setCamId(e.target.value)}><option value="">Kamera belakang (otomatis)</option>{cams.map(c=><option key={c.id} value={c.id}>{c.label||c.id}</option>)}</select></label>}
      <p className="muted" style={{fontSize:12}}>Arahkan QR Code anggota atau kode buku ke dalam kotak.</p>
    </div>
  </Modal>;
}
