import { useEffect, useRef, useState } from "react";
import { CameraScanner } from "./CameraScanner";
import { Modal } from "./Shared";
import { cameraError, createCamera } from "../lib/camera";

export function QRScanner({ onDetect, onClose }) {
  const [cams, setCams] = useState([]);
  const [camId, setCamId] = useState("");
  const [err, setErr] = useState("");
  const boxRef = useRef(null);
  const done = useRef(false);
  const cb = useRef(onDetect);
  cb.current = onDetect;

  useEffect(() => {
    setErr("");
    let alive = true;
    let cam = null;

    const t = setTimeout(() => {
      if (!alive || !boxRef.current) return;
      cam = createCamera(boxRef.current);
      cam.start((text) => {
        if (done.current) return;
        done.current = true;
        try {
          cb.current(text);
        } catch (e) {
          console.error(e);
        }
      }, camId).catch((e) => {
        if (alive) setErr(cameraError(e));
      });
    }, 100);

    return () => {
      alive = false;
      clearTimeout(t);
      if (cam) cam.stop();
    };
  }, [camId]);

  const [manual, setManual] = useState("");
  const submit = (e) => {
    e.preventDefault();
    if (manual.trim()) onDetect(manual.trim());
  };

  return (
    <Modal title="Pindai QR Code" close={onClose}>
      <div className="qr-shell" data-testid="qr-scanner">
        <div ref={boxRef} className="qr-camera-box" style={{ width: "100%", height: "300px", background: "#000", position: "relative" }}>
          <CameraScanner onCode={onDetect} testId="qr-camera" />
        </div>
        {err && <div className="p-3 text-sm text-red-500 bg-red-50">{err}</div>}
        <p className="muted" style={{ fontSize: 12 }}>Arahkan QR Code anggota atau ketik kodenya secara manual di bawah.</p>
        <form className="manual-row" onSubmit={submit}>
          <input
            data-testid="qr-manual-input"
            placeholder="Atau ketik kode (MB-xxxx)..."
            value={manual}
            onChange={(e) => setManual(e.target.value)}
            className="input"
          />
          <button type="submit" className="btn btn-secondary" data-testid="qr-manual-submit">Pakai</button>
        </form>
      </div>
    </Modal>
  );
}
