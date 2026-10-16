import { useEffect, useRef, useState } from "react";
 fitur/laporan-kartu-belakang-cetak-duplex
import { Camera, Crop, Upload, X } from "lucide-react";
import { PhotoCropper } from "./PhotoCropper";
import { readFile } from "../lib";

import { Camera, Crop, Loader2, Sparkles, Upload, X } from "lucide-react";
import { fmtSize, optimizeImage, prepareForCrop } from "../lib/image";
import { PhotoCropper } from "./PhotoCropper";
 main

export function Modal({ title, close, children, wide }) {
  const closeRef = useRef(close); closeRef.current = close; const boxRef = useRef(null);
  useEffect(() => { const onKey = (e) => { if (e.key !== "Escape") return; const all = document.querySelectorAll(".modal-backdrop"); if (all[all.length - 1] === boxRef.current) closeRef.current?.(); }; window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey); }, []);
  return <div ref={boxRef} className="modal-backdrop" data-testid="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
    <div className={wide ? "modal wide" : "modal"}><div className="modal-head"><h3>{title}</h3><button className="icon-button" data-testid="close-modal-button" onClick={close}><X size={18}/></button></div>{children}</div>
  </div>;
}

 fitur/laporan-kartu-belakang-cetak-duplex
const canDecode = (url) => new Promise((res) => { const i = new Image(); i.onload = () => res(true); i.onerror = () => res(false); i.src = url; });

export function PhotoBox({ value, onChange, label = "Foto", testId, compact, upload, onError }) {
  const inputRef = useRef(null); const [busy, setBusy] = useState(false); const [cropSrc, setCropSrc] = useState("");
  const fail = (err) => { const msg = err.response?.data?.detail || err.message || "Gagal mengunggah foto"; onError ? onError(msg) : alert(msg); };
  const pick = async (e) => {
    const file = e.target.files?.[0]; e.target.value = ""; if (!file) return;
    if (!upload) { try { onChange(await readFile(file)); } catch (err) { alert(err.message); } return; }
    if (file.size > 25 * 1024 * 1024) return fail(new Error("Ukuran foto maksimal 25MB"));
    const local = URL.createObjectURL(file);
    if (await canDecode(local)) { setCropSrc(local); return; }
    URL.revokeObjectURL(local); setBusy(true);
    try { const r = await upload(file); setCropSrc(r.url); } catch (err) { fail(err); } finally { setBusy(false); }
  };
  const closeCrop = () => { if (cropSrc.startsWith("blob:")) URL.revokeObjectURL(cropSrc); setCropSrc(""); };
  const saveCrop = async (file) => {
    try { const r = await upload(file); onChange(r.url); closeCrop(); } catch (err) { fail(err); }

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
 main
  };
  const recrop = () => setCropSrc(original.current.src || value);
  const done = ({ dataUrl, info: i }) => { onChange(dataUrl); setInfo({ ...i, before: original.current.before }); setCropSrc(""); };

  const infoText = (i) => i.cropped
    ? `Dipotong pas kartu · ${i.width}×${i.height}px · ${fmtSize(i.after)}${i.before ? ` (asli ${fmtSize(i.before)})` : ""}`
    : i.changed ? `Diperkecil otomatis ${fmtSize(i.before)} → ${fmtSize(i.after)} · ${i.width}×${i.height}px` : `Ukuran sudah pas (${fmtSize(i.after)}) · tidak diubah`;

  return <div className={compact ? "photo-box compact" : "photo-box"} data-testid={testId}>
    <div className={canCrop ? "photo-preview card-ratio" : "photo-preview"}>{busy ? <Loader2 size={24} className="spin"/> : value ? <img src={value} alt={label}/> : <Camera size={28}/>}</div>
    <div className="photo-actions">
      <button type="button" className="secondary" disabled={busy} data-testid={`${testId}-upload-button`} onClick={() => inputRef.current?.click()}><Upload size={14}/> {busy ? "Membaca foto..." : `Unggah ${label.toLowerCase()}`}</button>
      {value && !busy && upload && <button type="button" className="text-button" data-testid={`${testId}-recrop-button`} onClick={() => setCropSrc(value)}><Crop size={13}/> Atur posisi</button>}
      {value && !busy && <button type="button" className="text-button" data-testid={`${testId}-remove-button`} onClick={() => onChange("")}>Hapus</button>}
      <small>{upload ? "JPG/PNG/WEBP/HEIC · potong & geser dulu, lalu otomatis dikompres" : "JPG/PNG, maks 900KB"}</small>
      <input ref={inputRef} type="file" accept={upload ? "image/*,.heic,.heif" : "image/*"} hidden onChange={pick} data-testid={`${testId}-input`}/>
    </div>
    {cropSrc && <PhotoCropper src={cropSrc} onDone={saveCrop} close={closeCrop}/>}
  </div>;
}
