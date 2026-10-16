import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Cropper from "react-easy-crop";
import { Check, Loader2, Maximize, RotateCcw, RotateCw, X, ZoomIn, ZoomOut } from "lucide-react";
import { CARD_PHOTO, cropToDataUrl } from "../lib/image";

/** Jendela potong & geser foto anggota agar wajah pas di kotak ID card */
export function PhotoCropper({ src, onDone, onCancel }) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [area, setArea] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // Escape hanya menutup jendela modal cropper
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onCancel]);

  const onCropComplete = useCallback((_, croppedAreaPixels) => {
    setArea(croppedAreaPixels);
  }, []);

  const save = async () => {
    try {
      setBusy(true);
      setErr("");
      const file = await cropToDataUrl(src, area, rotation);
      onDone(file);
    } catch (e) {
      setErr(e.message || "Gagal memotong gambar");
      setBusy(false);
    }
  };

  return createPortal(
    <div className="modal-backdrop" onClick={onCancel}>
      <div
        className="modal cropper-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ width: "95vw", maxWidth: "600px", height: "85vh", display: "flex", flexDirection: "column" }}
      >
        <div className="modal-header">
          <h3>Sesuaikan Posisi & Ukuran Foto</h3>
          <button type="button" className="icon-btn" onClick={onCancel} disabled={busy}>
            <X size={18} />
          </button>
        </div>

        <div className="cropper-container" style={{ position: "relative", flex: 1, background: "#111", minHeight: "350px" }}>
          <Cropper
            image={src}
            crop={crop}
            zoom={zoom}
            rotation={rotation}
            aspect={CARD_PHOTO.width / CARD_PHOTO.height}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onRotationChange={setRotation}
            onCropComplete={onCropComplete}
          />
        </div>

        {err && <div className="p-3 text-sm text-red-500 bg-red-50 border-t">{err}</div>}

        <div className="cropper-toolbar p-4 bg-white border-t flex flex-col gap-3">
          <div className="flex items-center gap-4">
            <ZoomOut size={16} className="text-muted-foreground" />
            <input
              type="range"
              min={1}
              max={3}
              step={0.05}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="flex-1"
            />
            <ZoomIn size={16} className="text-muted-foreground" />
            <span className="text-xs w-10 text-right">{Math.round(zoom * 100)}%</span>
          </div>

          <div className="flex items-center justify-between pt-2 border-t">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn btn-sm btn-outline flex items-center gap-1"
                onClick={() => setRotation((r) => (r - 90) % 360)}
                title="Putar Kiri"
              >
                <RotateCcw size={14} /> Putar
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline flex items-center gap-1"
                onClick={() => {
                  setZoom(1);
                  setRotation(0);
                  setCrop({ x: 0, y: 0 });
                }}
                title="Reset Posisi"
              >
                <Maximize size={14} /> Reset
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>
                Batal
              </button>
              <button type="button" className="btn btn-primary flex items-center gap-1" onClick={save} disabled={busy}>
                {busy ? <Loader2 className="animate-spin" size={16} /> : <Check size={16} />}
                Simpan Foto
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
