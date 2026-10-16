import { useCallback, useState } from "react";
import { createPortal } from "react-dom";
import Cropper from "react-easy-crop";
import { Check, Move, ZoomIn } from "lucide-react";
import { Modal } from "./Shared";

export const PHOTO_ASPECT = 6 / 7;
const MAX_H = 1080;

async function cropToFile(src, area) {
  const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; });
  const scale = Math.min(1, MAX_H / area.height);
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(area.width * scale); canvas.height = Math.round(area.height * scale);
  const ctx = canvas.getContext("2d"); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(img, area.x, area.y, area.width, area.height, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.92));
  return new File([blob], "foto-potong.jpg", { type: "image/jpeg" });
}

export function PhotoCropper({ src, onDone, close }) {
  const [crop, setCrop] = useState({ x: 0, y: 0 }); const [zoom, setZoom] = useState(1); const [area, setArea] = useState(null); const [busy, setBusy] = useState(false);
  const onComplete = useCallback((_, px) => setArea(px), []);
  const confirm = async () => { if (!area) return; setBusy(true); try { await onDone(await cropToFile(src, area)); } finally { setBusy(false); } };
  return createPortal(<Modal title="Potong & atur posisi foto" close={close}>
    <div className="cropper-wrap" data-testid="photo-cropper">
      <div className="cropper-stage" data-testid="photo-cropper-stage">
        <Cropper image={src} crop={crop} zoom={zoom} aspect={PHOTO_ASPECT} minZoom={1} maxZoom={4} zoomSpeed={0.3} restrictPosition onCropChange={setCrop} onZoomChange={setZoom} onCropComplete={onComplete} showGrid objectFit="contain"/>
      </div>
      <p className="cropper-hint"><Move size={14}/> Geser foto supaya wajah berada di tengah kotak, cubit atau pakai penggeser untuk memperbesar.</p>
      <label className="cropper-zoom"><ZoomIn size={16}/><input type="range" min={1} max={4} step={0.01} value={zoom} data-testid="photo-cropper-zoom" onChange={(e) => setZoom(Number(e.target.value))}/></label>
      <div className="cropper-actions">
        <button type="button" className="secondary" data-testid="photo-cropper-cancel" onClick={close}>Batal</button>
        <button type="button" className="primary" data-testid="photo-cropper-confirm" disabled={busy || !area} onClick={confirm}><Check size={16}/> {busy ? "Menyimpan foto..." : "Pakai foto ini"}</button>
      </div>
    </div>
  </Modal>, document.body);
}
