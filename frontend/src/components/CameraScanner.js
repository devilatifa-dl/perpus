import { useEffect, useRef, useState } from "react";
import { Html5Qrcode, Html5QrcodeSupportedFormats } from "html5-qrcode";
import { CheckCircle2, RefreshCw, SwitchCamera, XCircle } from "lucide-react";

// Starts/stops are serialized so a new camera session never races the previous one (StrictMode, camera switch).
let chain = Promise.resolve();
const COOLDOWN_MS = 1000;
const SAME_CODE_MS = 5000;

export function cameraErrorText(e) {
  const t = `${e?.name || ""} ${e?.message || ""} ${typeof e === "string" ? e : ""}`;
  if (!window.isSecureContext) return "Kamera hanya bisa dibuka lewat alamat aman (https).";
  if (/NotAllowed|Permission|denied/i.test(t)) return "Izin kamera ditolak. Izinkan akses kamera untuk situs ini di pengaturan browser, lalu tekan Coba lagi. Jika dibuka di dalam aplikasi lain, buka langsung di Chrome/Safari.";
  if (/NotFound|DevicesNotFound|Overconstrained|no camera/i.test(t)) return "Kamera tidak ditemukan di perangkat ini. Gunakan input kode manual.";
  if (/NotReadable|TrackStart|in use|Could not start|AbortError/i.test(t)) return "Kamera sedang dipakai aplikasi lain. Tutup aplikasi itu lalu tekan Coba lagi.";
  return "Kamera tidak dapat dibuka. Tekan Coba lagi atau gunakan input kode manual.";
}

const errDetail = (e) => String(e?.name || e?.message || e || "").slice(0, 120);
const isDenied = (e) => /NotAllowed|Permission|denied/i.test(`${e?.name || ""} ${e?.message || ""} ${e}`);

async function startWithFallback(scanner, config, onScan, facing) {
  try { return await scanner.start({ facingMode: facing }, config, onScan, () => {}); }
  catch (first) {
    if (isDenied(first)) throw first;
    const cams = await Html5Qrcode.getCameras().catch(() => []);
    if (!cams.length) throw first;
    const back = cams.find((c) => /back|rear|belakang|environment/i.test(c.label)) || cams[cams.length - 1];
    const pick = facing === "user" ? cams[0] : back;
    try { await scanner.stop(); } catch (_) { /* belum berjalan */ }
    return scanner.start(pick.id, config, onScan, () => {});
  }
}

export function CameraScanner({ onCode, testId = "camera-scanner" }) {
  const hostRef = useRef(null); const cb = useRef(onCode); const last = useRef({ code: "", at: 0 }); const lockUntil = useRef(0); const fbTimer = useRef(null);
  const [facing, setFacing] = useState("environment"); const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState("starting"); const [err, setErr] = useState(""); const [detail, setDetail] = useState(""); const [multi, setMulti] = useState(false);
  const [fb, setFb] = useState(null);
  cb.current = onCode;
  useEffect(() => () => clearTimeout(fbTimer.current), []);
  useEffect(() => {
    let cancelled = false; let scanner = null;
    const el = document.createElement("div");
    el.id = `qr-${Math.random().toString(36).slice(2)}`; el.className = "cam-video";
    hostRef.current.appendChild(el);
    setStatus("starting"); setErr(""); setDetail("");
    const onScan = async (text) => {
      const now = Date.now();
      if (cancelled || now < lockUntil.current) return;
      if (text === last.current.code && now - last.current.at < SAME_CODE_MS) return;
      last.current = { code: text, at: now }; lockUntil.current = now + 60000;
      setFb({ state: "busy", title: "Memproses…" });
      let r;
      try { r = await cb.current(text); } catch (_) { r = { ok: false, title: "Gagal memproses" }; }
      if (cancelled) return;
      const res = r && typeof r === "object" ? r : { ok: true, title: "QR terbaca" };
      setFb({ state: res.ok ? "ok" : "fail", title: res.title, sub: res.sub });
      lockUntil.current = Date.now() + COOLDOWN_MS;
      clearTimeout(fbTimer.current); fbTimer.current = setTimeout(() => setFb(null), COOLDOWN_MS);
    };
    chain = chain.then(async () => {
      if (cancelled) return;
      if (!navigator.mediaDevices?.getUserMedia) { setStatus("error"); setErr(cameraErrorText({ name: window.isSecureContext ? "NotFound" : "" })); return; }
      scanner = new Html5Qrcode(el.id, { verbose: false, formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE] });
      const qrbox = (w, h) => { const s = Math.max(150, Math.floor(Math.min(w, h) * 0.75)); return { width: Math.min(s, w), height: Math.min(s, h) }; };
      try {
        await startWithFallback(scanner, { fps: 15, qrbox, disableFlip: false }, onScan, facing);
        if (cancelled) return;
        setStatus("live");
        Html5Qrcode.getCameras().then((c) => !cancelled && setMulti(c.length > 1)).catch(() => {});
      } catch (e) { if (!cancelled) { setStatus("error"); setErr(cameraErrorText(e)); setDetail(errDetail(e)); } }
    });
    return () => {
      cancelled = true;
      chain = chain.then(async () => { try { if (scanner?.isScanning) await scanner.stop(); } catch (_) { /* sudah berhenti */ } el.remove(); });
    };
  }, [facing, attempt]);
  return <div className="cam-shell" data-testid={testId} data-status={status}>
    <div ref={hostRef} className="cam-host"/>
    {status === "starting" && <div className="cam-overlay" data-testid={`${testId}-starting`}>Membuka kamera… izinkan akses kamera jika diminta.</div>}
    {status === "error" && <div className="cam-overlay error-state" data-testid={`${testId}-error`}><p>{err}</p>{detail && <small className="cam-detail">Kode error: {detail}</small>}<button type="button" className="secondary" data-testid={`${testId}-retry`} onClick={() => setAttempt((a) => a + 1)}><RefreshCw size={15}/> Coba lagi</button></div>}
    {fb && <div className={`cam-feedback ${fb.state}`} data-testid={`${testId}-feedback`} data-state={fb.state}>
      {fb.state === "ok" && <CheckCircle2 size={54}/>}{fb.state === "fail" && <XCircle size={54}/>}
      <b data-testid={`${testId}-feedback-title`}>{fb.title}</b>{fb.sub && <span>{fb.sub}</span>}
      {fb.state !== "busy" && <i className="cam-cooldown"/>}
    </div>}
    {status === "live" && multi && <button type="button" className="cam-switch" title="Ganti kamera depan/belakang" data-testid={`${testId}-switch`} onClick={() => setFacing((f) => (f === "environment" ? "user" : "environment"))}><SwitchCamera size={16}/> {facing === "environment" ? "Kamera depan" : "Kamera belakang"}</button>}
  </div>;
}
