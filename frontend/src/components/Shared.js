import { useRef } from "react";
import { Camera, Upload, X } from "lucide-react";
import { readFile } from "../lib";

export function Modal({ title, close, children, wide }) {
  return <div className="modal-backdrop" data-testid="modal-backdrop" onClick={(e) => { if (e.target.classList.contains("modal-backdrop")) close(); }}>
    <div className={wide ? "modal wide" : "modal"}><div className="modal-head"><h3>{title}</h3><button className="icon-button" data-testid="close-modal-button" onClick={close}><X size={18}/></button></div>{children}</div>
  </div>;
}

export function PhotoBox({ value, onChange, label = "Foto", testId, compact }) {
  const inputRef = useRef(null);
  const pick = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    try { onChange(await readFile(file)); } catch (err) { alert(err.message); }
  };
  return <div className={compact ? "photo-box compact" : "photo-box"} data-testid={testId}>
    <div className="photo-preview">{value ? <img src={value} alt={label}/> : <Camera size={28}/>}</div>
    <div className="photo-actions">
      <button type="button" className="secondary" data-testid={`${testId}-upload-button`} onClick={() => inputRef.current?.click()}><Upload size={14}/> Unggah {label.toLowerCase()}</button>
      {value && <button type="button" className="text-button" data-testid={`${testId}-remove-button`} onClick={() => onChange("")}>Hapus</button>}
      <small>JPG/PNG, maks 900KB</small>
      <input ref={inputRef} type="file" accept="image/*" hidden onChange={pick} data-testid={`${testId}-input`}/>
    </div>
  </div>;
}
