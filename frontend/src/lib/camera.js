import { Html5Qrcode, Html5QrcodeSupportedFormats } from "html5-qrcode";

// Status html5-qrcode: 1 = belum mulai, 2 = memindai, 3 = dijeda
const SCANNING = 2;
const PAUSED = 3;

const qrbox = (w, h) => {
  const s = Math.max(140, Math.floor(Math.min(w, h) * 0.7));
  return { width: s, height: s };
};

// html5-qrcode memanggil video.play() tanpa menangani promise-nya. Jika kamera ditutup cepat,
// browser melempar "play() request was interrupted" yang tidak berbahaya. Redam pesan itu saja.
if (typeof window !== "undefined" && !window.__qrPlayGuard) {
  window.__qrPlayGuard = true;
  // Tandai promise video.play() sebagai "ditangani" (pemanggil tetap menerima hasil/error aslinya)
  try {
    const origPlay = window.HTMLMediaElement.prototype.play;
    window.HTMLMediaElement.prototype.play = function patchedPlay(...args) {
      const p = origPlay.apply(this, args);
      if (this.tagName === "VIDEO" && p && typeof p.catch === "function") p.catch(() => {});
      return p;
    };
  } catch (e) { /* browser lama */ }
  window.addEventListener("unhandledrejection", (ev) => {
    const m = String(ev?.reason?.message || ev?.reason || "");
    if (/play\(\) request was interrupted|The play\(\) request|media was removed|RenderedCamera has already been closed/i.test(m)) ev.preventDefault();
  });
}

export function cameraError(e) {
  const msg = String(e?.name || "") + " " + String(e?.message || e || "");
  if (typeof window !== "undefined" && window.isSecureContext === false) return "Kamera hanya bisa dipakai lewat alamat https.";
  if (/NotAllowed|Permission|denied/i.test(msg)) return "Izin kamera ditolak. Buka pengaturan browser, izinkan kamera untuk situs ini, lalu nyalakan kamera lagi.";
  if (/NotReadable|TrackStart|in use|Could not start/i.test(msg)) return "Kamera sedang dipakai aplikasi lain. Tutup aplikasi kamera lain lalu coba lagi.";
  if (/NotFound|no camera|Requested device not found|DevicesNotFound/i.test(msg)) return "Kamera tidak ditemukan. Gunakan alat pemindai atau ketik kode.";
  return "Kamera belum bisa dibuka. Coba matikan lalu nyalakan kamera lagi.";
}

let seq = 0;

/**
 * Kamera QR yang aman untuk HP.
 * - Setiap kamera punya elemen sendiri (tidak saling hapus video).
 * - Kamera belakang otomatis, kotak pindai menyesuaikan layar.
 * - Berhenti tanpa error walau kamera belum selesai terbuka.
 */
export function createCamera(container) {
  const el = document.createElement("div");
  el.id = `qr-cam-${Date.now()}-${++seq}`;
  el.className = "qr-cam-surface";
  container.appendChild(el);
  const scanner = new Html5Qrcode(el.id, {
    verbose: false,
    formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
    experimentalFeatures: { useBarCodeDetectorIfSupported: true },
  });
  let closed = false;
  let pending = Promise.resolve();
  const config = { fps: 12, qrbox };
  const state = () => { try { return scanner.getState(); } catch (e) { return 1; } };

  const stop = async () => {
    closed = true;
    try { await pending; } catch (e) { /* start gagal */ }
    try { if (state() === SCANNING || state() === PAUSED) await scanner.stop(); } catch (e) { /* sudah berhenti */ }
    try { scanner.clear(); } catch (e) { /* sudah bersih */ }
    try { el.remove(); } catch (e) { /* sudah dilepas */ }
  };

  const run = async (src, onDecode) => {
    pending = scanner.start(src, config, (text) => { if (!closed) onDecode(text); }, () => {});
    await pending;
    if (closed) await stop();
  };

  const start = async (onDecode, cameraId) => {
    if (closed) return;
    try { await run(cameraId || { facingMode: "environment" }, onDecode); return; }
    catch (e) {
      if (cameraId || closed || /NotAllowed|Permission|denied/i.test(String(e?.name || e))) throw e;
      // Cadangan: pilih kamera dari daftar perangkat (utamakan kamera belakang)
      const cams = await Html5Qrcode.getCameras();
      const cam = cams.find((c) => /back|belakang|rear|environment/i.test(c.label)) || cams[cams.length - 1];
      if (!cam) throw e;
      if (closed) return;
      await run(cam.id, onDecode);
    }
  };

  return { start, stop };
}

// Satu AudioContext dipakai ulang (iOS membatasi jumlahnya)
let audioCtx = null;
export function unlockAudio() {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
  } catch (e) { /* audio tidak tersedia */ }
}
export function beep(ok = true) {
  try {
    unlockAudio();
    if (audioCtx) {
      const o = audioCtx.createOscillator(); const g = audioCtx.createGain();
      o.frequency.value = ok ? 880 : 240; o.connect(g); g.connect(audioCtx.destination); g.gain.value = 0.08;
      o.start(); o.stop(audioCtx.currentTime + (ok ? 0.14 : 0.32));
    }
  } catch (e) { /* audio tidak tersedia */ }
  try { navigator.vibrate?.(ok ? 80 : [60, 60, 60]); } catch (e) { /* getar tidak tersedia */ }
}
