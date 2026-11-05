import { useEffect, useRef, useState } from "react";
import { DoorClosed, DoorOpen, Clock, ScanLine, Volume2, VolumeX } from "lucide-react";
import { scanSound, scanSoundEnabled, setScanSoundEnabled } from "../lib/camera";

const SAMPLES = [
  { key: "masuk", label: "Masuk", hint: "2 nada naik", Icon: DoorOpen },
  { key: "keluar", label: "Keluar", hint: "3 nada turun", Icon: DoorClosed },
  { key: "sudah_masuk", label: "Baru dipindai", hint: "2 ketukan", Icon: Clock },
  { key: "error", label: "Gagal", hint: "dengung rendah", Icon: ScanLine },
];

// Tombol bunyi di panel kiosk Pengunjung: nyalakan/matikan bunyi scan + coba tiap bunyi
export function SoundControl() {
  const [on, setOn] = useState(scanSoundEnabled());
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const esc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", close); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("pointerdown", close); document.removeEventListener("keydown", esc); };
  }, [open]);
  const toggle = () => { const v = !on; setOn(v); setScanSoundEnabled(v); if (v) scanSound("masuk", { force: true }); };

  return <div className="sound-ctl" ref={ref}>
    <button type="button" className={`icon-button${on ? "" : " muted"}`} title={on ? "Bunyi scan: nyala" : "Bunyi scan: mati"} aria-label="Pengaturan bunyi scan" aria-expanded={open} data-testid="visit-sound-button" data-sound={on ? "on" : "off"} onClick={() => setOpen((x) => !x)}>{on ? <Volume2 size={17}/> : <VolumeX size={17}/>}</button>
    {open && <div className="sound-pop" role="dialog" aria-label="Bunyi scan" data-testid="visit-sound-panel">
      <div className="sound-pop-head"><div><b>Bunyi scan</b><small>Beda bunyi untuk masuk &amp; keluar</small></div>
        <button type="button" role="switch" aria-checked={on} className={`sound-switch${on ? " on" : ""}`} data-testid="visit-sound-toggle" onClick={toggle}><i/><span>{on ? "Nyala" : "Mati"}</span></button></div>
      <div className="sound-samples">
        {SAMPLES.map(({ key, label, hint, Icon }) => <button type="button" key={key} className={`sound-sample s-${key}`} data-testid={`visit-sound-test-${key}`} onClick={() => scanSound(key, { force: true })}><Icon size={15}/><span><b>{label}</b><small>{hint}</small></span></button>)}
      </div>
      <p className="sound-note">Tekan untuk mencoba. Di HP, getarannya juga berbeda. Pastikan HP tidak dalam mode senyap.</p>
    </div>}
  </div>;
}
