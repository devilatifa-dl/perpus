import { useEffect, useRef, useState } from "react";
import { Camera, Crop, Loader2, Sparkles, Upload, X } from "lucide-react";
import { PhotoCropper } from "./PhotoCropper";
import { fmtSize, optimizeImage, prepareForCrop, readFile } from "../utils/image";

export function PhotoBox({ value, onChange, label = "Foto", upload, aspect = 1 }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [cropSrc, setCropSrc] = useState("");
  const original = useRef({ src: "", before: 0 });

  const fail = (err) => {
    const msg = err.response?.data?.detail || err.message || "Gagal memproses gambar";
    setErr(msg);
    setBusy(false);
  };

  const saveCrop = async (croppedUrl) => {
    try {
      setBusy(true);
      const res = await fetch(croppedUrl);
      const blob = await res.blob();
      const file = new File([blob], "photo.jpg", { type: "image/jpeg" });
      onChange(file);
      setCropSrc("");
      setBusy(false);
    } catch (e) {
      fail(e);
    }
  };

  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      <div className="flex items-center gap-4">
        {value ? (
          <div className="relative w-24 h-24 border rounded-lg overflow-hidden">
            <img src={typeof value === "string" ? value : URL.createObjectURL(value)} alt="Preview" className="w-full h-full object-cover" />
            <button
              type="button"
              onClick={() => onChange("")}
              className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 shadow"
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <div
            onClick={() => !busy && inputRef.current?.click()}
            className="w-24 h-24 border-2 border-dashed rounded-lg flex flex-col items-center justify-center cursor-pointer hover:border-gray-400"
          >
            {busy ? <Loader2 className="animate-spin" size={20} /> : <Upload size={20} />}
            <span className="text-xs mt-1">Upload</span>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            e.target.value = "";
            setErr("");
            setCropSrc(URL.createObjectURL(file));
          }}
        />
      </div>
      {err && <p className="text-xs text-red-500">{err}</p>}
      {cropSrc && (
        <Photocropper
          src={cropSrc}
          aspect={aspect}
          onCancel={() => setCropSrc("")}
          onComplete={saveCrop}
        />
      )}
    </div>
  );
}

export function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">{title}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 font-bold">✕</button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}
