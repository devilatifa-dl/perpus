import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Cropper from "react-easy-crop";
import { Check, Loader2, Maximize, RotateCcw, RotateCw, X, ZoomIn, ZoomOut } from "lucide-react";
import { CARD_PHOTO, cropToDataUrl } from "../lib/image";

/** Jendela potong & geser foto anggota agar wajah pas di kotak foto kartu (rasio 6:7). */
export function PhotoCropper({ src, onDone, onCancel }) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [area, setArea] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // Escape hanya menutup jendela potong (bukan form di belakangnya)
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") { e.stopImmediatePropagation(); onCancel(); } };
    window.addEventListener("keydown", onKey, true);
    const prev = document.body.style.overflow; document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey, true); document.body.style.overflow = prev; };
  }, [onCancel]);

  const onComplete = useCallback((_, px) => setArea(px), []);
  const reset = () => { setCrop({ x: 0, y: 0 }); setZoom(1); setRotation(0); };
  const z = (d) => setZoom((v) => Math.min(4, Math.max(1, +(v + d).toFixed(2))));

  const apply = async () => {
    if (!area) return;
    setBusy(true); setErr("");
    try { onDone(await cropToDataUrl(src, area, rotation)); }
    catch (e) { setErr(e.message || "Foto gagal dipotong"); setBusy(false); }
  };

  return createPortal(<div className="crop-backdrop" data-testid="photo-cropper">
    <div className="crop-modal" role="dialog" aria-label="Potong foto">
      <div className="crop-head">
        <div><h3>Atur foto kartu</h3><p>Geser foto agar wajah berada di dalam garis oval.</p></div>
        <button type="button" className="icon-button" data-testid="crop-cancel-icon" onClick={onCancel} aria-label="Tutup"><X size={18}/></button>
      </div>
      <div className="crop-stage" data-testid="crop-stage">
        <Cropper
          image={src}
          crop={crop} zoom={zoom} rotation={rotation}
          aspect={CARD_PHOTO.width / CARD_PHOTO.height}
          minZoom={1} maxZoom={4} zoomSpeed={0.25}
          showGrid restrictPosition objectFit="contain"
          onCropChange={setCrop} onZoomChange={setZoom} onRotationChange={setRotation} onCropComplete={onComplete}
          classes={{ cropAreaClassName: "crop-area-face" }}
        />
      </div>
      <div className="crop-controls">
        <div className="crop-zoom">
          <button type="button" className="icon-button" data-testid="crop-zoom-out" onClick={() => z(-0.2)} aria-label="Perkecil"><ZoomOut size={17}/></button>
          <input type="range" min={1} max={4} step={0.01} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} data-testid="crop-zoom-slider" aria-label="Perbesar foto"/>
          <button type="button" className="icon-button" data-testid="crop-zoom-in" onClick={() => z(0.2)} aria-label="Perbesar"><ZoomIn size={17}/></button>
        </div>
        <div className="crop-tools">
          <button type="button" className="secondary" data-testid="crop-rotate-left" onClick={() => setRotation((r) => (r - 90 + 360) % 360)}><RotateCcw size={15}/> Putar kiri</button>
          <button type="button" className="secondary" data-testid="crop-rotate-right" onClick={() => setRotation((r) => (r + 90) % 360)}><RotateCw size={15}/> Putar kanan</button>
          <button type="button" className="secondary" data-testid="crop-reset" onClick={reset}><Maximize size={15}/> Atur ulang</button>
        </div>
        <p className="crop-hint">Di HP: geser dengan satu jari, cubit dua jari untuk zoom. Hasil {CARD_PHOTO.width}×{CARD_PHOTO.height}px sesuai kotak foto kartu.</p>
        {err && <div className="error" data-testid="crop-error">{err}</div>}
      </div>
      <div className="crop-actions">
        <button type="button" className="secondary" data-testid="crop-cancel-button" onClick={onCancel} disabled={busy}>Batal</button>
        <button type="button" className="primary" data-testid="crop-apply-button" onClick={apply} disabled={busy || !area}>{busy ? <><Loader2 size={16} className="spin"/> Memproses...</> : <><Check size={16}/> Gunakan foto</>}</button>
      </div>
    </div>
  </div>, document.body);
}
