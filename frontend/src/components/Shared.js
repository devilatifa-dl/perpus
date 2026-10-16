import { useEffect, useRef, useState } from "react";
import { Camera, Crop, Loader2, Sparkles, Upload, X } from "lucide-react";
import { fmtSize, optimizeImage, prepareForCrop } from "../lib/image";
import { PhotoCropper } from "./PhotoCropper";

export function Modal({ title, close, children, wide }) {
  const closeRef = useRef(close); closeRef.current = close;
  useEffect(() => { const onKey = (e) => { if (e.key === "Escape") closeRef.current?.(); }; window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey); }, []);
  return <div className="modal-backdrop" data-testid="modal-backdrop" onClick={(e) => { if (e.target.classList.contains("modal-backdrop")) close(); }}>
    <div className={wide ? "modal wide" : "modal"}><div className="modal-head"><h3>{title}</h3><button className="icon-button" data-testid="close-modal-button" onClick={close}><X size={18}/></button></div>{children}</div>
  </div>;
}

const kindOf = (label, kind) => kind || (/logo/i.test(label) ? "logo" : /sampul|cover/i.test(label) ? "cover" : "photo");

export function PhotoBox({ value, onChange, label = "Foto", testId, compact, kind }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [cropSrc, setCropSrc] = useState("");
  const original = useRef({ src: "", before: 0 });
  const k = kindOf(label, kind);
  const canCrop = k === "photo";

  const pick = async (e) => {
    const file = e.target.files?.[0]; e.target.value = "";
    if (!file) return;
    setBusy(true); setErr("");
    try {
      if (canCrop) {
        const prep = await prepareForCrop(file);
        original.current = prep;
        setCropSrc(prep.src);
      } else {
        const { dataUrl, info: i } = await optimizeImage(file, k);
        onChange(dataUrl); setInfo(i);
      }
    } catch (er) { setErr(er.message || "Gambar tidak dapat diproses"); }
    finally { setBusy(false); }
  };
  const recrop = () => setCropSrc(original.current.src || value);
  const done = ({ dataUrl, info: i }) => { onChange(dataUrl); setInfo({ ...i, before: original.current.before }); setCropSrc(""); };

  const infoText = (i) => i.cropped
    ? `Dipotong pas kartu · ${i.width}×${i.height}px · ${fmtSize(i.after)}${i.before ? ` (asli ${fmtSize(i.before)})` : ""}`
    : i.changed ? `Diperkecil otomatis ${fmtSize(i.before)} → ${fmtSize(i.after)} · ${i.width}×${i.height}px` : `Ukuran sudah pas (${fmtSize(i.after)}) · tidak diubah`;

  return <div className={compact ? "photo-box compact" : "photo-box"} data-testid={testId}>
    <div className={canCrop ? "photo-preview card-ratio" : "photo-preview"}>{busy ? <Loader2 size={24} className="spin"/> : value ? <img src={value} alt={label}/> : <Camera size={28}/>}</div>
    <div className="photo-actions">
      <div className="photo-btn-row">
        <button type="button" className="secondary" data-testid={`${testId}-upload-button`} disabled={busy} onClick={() => inputRef.current?.click()}><Upload size={14}/> {busy ? "Menyiapkan..." : `Unggah ${label.toLowerCase()}`}</button>
        {canCrop && value && !busy && <button type="button" className="secondary" data-testid={`${testId}-crop-button`} onClick={recrop}><Crop size={14}/> Potong / geser</button>}
      </div>
      {value && !busy && <button type="button" className="text-button" data-testid={`${testId}-remove-button`} onClick={() => { onChange(""); setInfo(null); original.current = { src: "", before: 0 }; }}>Hapus</button>}
      {err ? <small className="photo-err" data-testid={`${testId}-error`}>{err}</small>
        : info ? <small className="photo-info" data-testid={`${testId}-info`}><Sparkles size={11}/> {infoText(info)}</small>
        : <small>{canCrop ? "JPG/PNG/WEBP, ukuran berapa pun — bisa dipotong & digeser" : "JPG/PNG/WEBP, ukuran berapa pun — otomatis diperkecil"}</small>}
      <input ref={inputRef} type="file" accept="image/*" hidden onChange={pick} data-testid={`${testId}-input`}/>
    </div>
    {cropSrc && <PhotoCropper src={cropSrc} onDone={done} onCancel={() => setCropSrc("")}/>}
  </div>;
}
