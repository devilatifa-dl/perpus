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
export function beep(ok = true) { scanSound(ok ? "masuk" : "error"); }

/* ---------- Bunyi hasil scan pengunjung: tiap hasil punya nada & getar berbeda ----------
   masuk  : dua nada NAIK cepat (ding-DING)        · getar 1x pendek
   keluar : tiga nada TURUN (DING-ding-dong)       · getar 2x
   sudah  : dua ketukan nada sama (tuk-tuk)        · getar 1x sangat pendek  (sudah_masuk / sudah_keluar / duplikat)
   error  : dengung rendah panjang                 · getar 3x                                                     */
const SOUNDS = {
  masuk: { notes: [[660, 0, 0.11], [990, 0.12, 0.16]], type: "sine", vib: 90 },
  keluar: { notes: [[990, 0, 0.1], [784, 0.11, 0.1], [523, 0.22, 0.2]], type: "sine", vib: [70, 60, 70] },
  sudah: { notes: [[587, 0, 0.07], [587, 0.12, 0.07]], type: "triangle", vib: 40 },
  error: { notes: [[220, 0, 0.36]], type: "square", vib: [60, 60, 60, 60, 60], gain: 0.05 },
};
const SOUND_KEY = "perpus-scan-sound";
export const scanSoundEnabled = () => { try { return localStorage.getItem(SOUND_KEY) !== "off"; } catch (e) { return true; } };
export const setScanSoundEnabled = (on) => { try { localStorage.setItem(SOUND_KEY, on ? "on" : "off"); } catch (e) { /* abaikan */ } };
export const soundKind = (action) => (action === "masuk" || action === "keluar" ? action : action === "error" ? "error" : "sudah");

export function scanSound(action, { force = false } = {}) {
  const s = SOUNDS[soundKind(action)];
  if (!force && !scanSoundEnabled()) return;
  try { window.__lastScanSound = { kind: soundKind(action), at: Date.now() }; } catch (e) { /* abaikan */ }
  try {
    unlockAudio();
    if (audioCtx) {
      const t0 = audioCtx.currentTime + 0.01; const peak = s.gain || 0.12;
      s.notes.forEach(([f, at, dur]) => {
        const o = audioCtx.createOscillator(); const g = audioCtx.createGain();
        o.type = s.type; o.frequency.value = f; o.connect(g); g.connect(audioCtx.destination);
        // envelope singkat supaya tidak berbunyi "klik"
        g.gain.setValueAtTime(0.0001, t0 + at);
        g.gain.exponentialRampToValueAtTime(peak, t0 + at + 0.012);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + at + dur);
        o.start(t0 + at); o.stop(t0 + at + dur + 0.02);
      });
    }
  } catch (e) { /* audio tidak tersedia */ }
  try { navigator.vibrate?.(s.vib); } catch (e) { /* getar tidak tersedia */ }
}
