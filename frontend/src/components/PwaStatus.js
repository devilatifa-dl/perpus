import { useEffect, useRef, useState } from "react";
import { CloudOff, Download, RefreshCw, Share, Smartphone, Wifi, X } from "lucide-react";
import { applyUpdate, canPromptInstall, isIOS, isStandalone, promptInstall } from "../pwa";
import { API } from "../lib";
import "../Pwa.css";

const DISMISS_KEY = "perpus-pwa-install-dismissed";
const DISMISS_DAYS = 14;
// Percobaan otomatis saat server lambat: 2s, 3s, 5s, 8s, 13s, 20s (maks 6 kali)
const AUTO_RETRY_BASE_MS = 2000;
const AUTO_RETRY_MAX_MS = 20000;
const AUTO_RETRY_MAX = 6;
const dismissedRecently = () => { try { const t = Number(localStorage.getItem(DISMISS_KEY) || 0); return t && Date.now() - t < DISMISS_DAYS * 864e5; } catch { return false; } };
const fmtTime = (iso) => { if (!iso) return ""; const d = new Date(iso); if (Number.isNaN(d.getTime())) return ""; return d.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); };

export function usePwaInstall() {
  const [installable, setInstallable] = useState(canPromptInstall());
  const [installed, setInstalled] = useState(isStandalone());
  useEffect(() => {
    const a = (e) => setInstallable(!!e.detail);
    const b = () => setInstalled(true);
    window.addEventListener("perpus:installable", a); window.addEventListener("perpus:installed", b);
    return () => { window.removeEventListener("perpus:installable", a); window.removeEventListener("perpus:installed", b); };
  }, []);
  return { installable, installed, ios: isIOS() && !installed, install: promptInstall };
}

export function InstallAppButton({ className = "pwa-inline-install", testId = "pwa-inline-install-button" }) {
  const { installable, installed, ios, install } = usePwaInstall();
  const [hint, setHint] = useState(false);
  if (installed || (!installable && !ios)) return null;
  return <div className="pwa-inline-wrap">
    <button type="button" className={className} data-testid={testId} onClick={() => (installable ? install() : setHint((v) => !v))}><Smartphone size={15}/> Pasang aplikasi di HP</button>
    {hint && <p className="pwa-inline-hint" data-testid="pwa-ios-hint">Di Safari: ketuk <Share size={13}/> <b>Bagikan</b>, lalu pilih <b>Tambah ke Layar Utama</b>.</p>}
  </div>;
}

export default function PwaStatus() {
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  const [backOnline, setBackOnline] = useState(false);
  const [cachedAt, setCachedAt] = useState("");
  const [update, setUpdate] = useState(false);
  const [showInstall, setShowInstall] = useState(false);
  const { installable, installed, ios, install } = usePwaInstall();

  useEffect(() => {
    const goOffline = () => { setOnline(false); setBackOnline(false); };
    const goOnline = () => { setOnline(true); setBackOnline(true); };
    const cached = (e) => setCachedAt(e.detail?.cachedAt || new Date().toISOString());
    const upd = () => setUpdate(true);
    window.addEventListener("offline", goOffline); window.addEventListener("online", goOnline);
    window.addEventListener("perpus:cached-data", cached); window.addEventListener("perpus:sw-update", upd);
    return () => {
      window.removeEventListener("offline", goOffline); window.removeEventListener("online", goOnline);
      window.removeEventListener("perpus:cached-data", cached); window.removeEventListener("perpus:sw-update", upd);
    };
  }, []);

  useEffect(() => {
    if (installed || dismissedRecently() || (!installable && !ios)) { setShowInstall(false); return undefined; }
    const t = setTimeout(() => setShowInstall(true), 3500);
    return () => clearTimeout(t);
  }, [installable, installed, ios]);

  // Pemberitahuan offline / server lambat hilang sendiri setelah 3 detik
  const [noticeVisible, setNoticeVisible] = useState(true);
  useEffect(() => {
    if (online && !cachedAt) return undefined;
    setNoticeVisible(true);
    // Saat server lambat, banner dibiarkan tampil selama percobaan otomatis berjalan
    if (cachedAt && online) return undefined;
    const t = setTimeout(() => setNoticeVisible(false), 3000);
    return () => clearTimeout(t);
  }, [online, cachedAt]);

  // Server lambat: coba lagi otomatis sampai data terbaru berhasil dimuat.
  // Begitu server merespons normal (bukan dari cache), halaman dimuat ulang sekali
  // agar semua data tampil segar tanpa perlu menekan tombol.
  const [autoTries, setAutoTries] = useState(0);
  const reloadedRef = useRef(false);

  useEffect(() => {
    if (!cachedAt || !online) { setAutoTries(0); return undefined; }
    if (autoTries >= AUTO_RETRY_MAX) return undefined;

    let cancelled = false;
    const delay = Math.min(AUTO_RETRY_BASE_MS * Math.pow(1.6, autoTries), AUTO_RETRY_MAX_MS);

    const t = setTimeout(async () => {
      if (cancelled) return;
      try {
        // Ping ringan dengan penanda agar service worker tidak menyajikan salinan cache.
        const res = await fetch(`${API}/health?fresh=${Date.now()}`, {
          cache: "no-store",
          headers: { "x-perpus-fresh": "1" },
        });
        if (cancelled) return;
        if (res.ok) {
          // Server sudah normal -> muat ulang sekali agar data segar tampil.
          if (!reloadedRef.current) {
            reloadedRef.current = true;
            window.location.reload();
            return;
          }
        }
      } catch {
        /* masih lambat / offline, coba lagi di putaran berikutnya */
      }
      if (!cancelled) setAutoTries((n) => n + 1);
    }, delay);

    return () => { cancelled = true; clearTimeout(t); };
  }, [cachedAt, online, autoTries]);

  const dismissInstall = () => { try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch { /* */ } setShowInstall(false); };
  const doInstall = async () => { const r = await install(); if (r !== "unavailable") setShowInstall(false); };
  const refresh = () => window.location.reload();

  let status = null;
  if (!online) {
    status = noticeVisible && <div className="pwa-pill offline" role="status" data-testid="pwa-offline-banner"><CloudOff size={15}/><span><b>Sedang offline</b> · menampilkan konten tersimpan{cachedAt ? ` (diperbarui ${fmtTime(cachedAt)})` : ""}</span></div>;
  } else if (backOnline) {
    status = <div className="pwa-pill online" role="status" data-testid="pwa-back-online-banner"><Wifi size={15}/><span><b>Kembali online</b></span><button type="button" data-testid="pwa-refresh-button" onClick={refresh}><RefreshCw size={13}/> Muat data terbaru</button><button type="button" className="pwa-x" aria-label="Tutup" data-testid="pwa-back-online-close" onClick={() => { setBackOnline(false); setCachedAt(""); }}><X size={14}/></button></div>;
  } else if (cachedAt) {
    const exhausted = autoTries >= AUTO_RETRY_MAX;
    status = noticeVisible && <div className="pwa-pill cached" role="status" data-testid="pwa-cached-banner">
      <CloudOff size={15}/>
      <span>
        {exhausted
          ? <>Server lambat · menampilkan data tersimpan ({fmtTime(cachedAt)})</>
          : <>Server lambat · memuat ulang otomatis{autoTries > 0 ? ` (${autoTries}/${AUTO_RETRY_MAX})` : ""}…</>}
      </span>
      <button type="button" data-testid="pwa-cached-refresh-button" onClick={refresh}><RefreshCw size={13}/> Muat sekarang</button>
      <button type="button" className="pwa-x" aria-label="Tutup" onClick={() => setCachedAt("")}><X size={14}/></button>
    </div>;
  }

  return <div className="pwa-layer" data-testid="pwa-status-layer">
    {status && <div className="pwa-top">{status}</div>}
    <div className="pwa-bottom">
      {update && <div className="pwa-card update" role="alert" data-testid="pwa-update-card"><span className="pwa-card-icon"><RefreshCw size={18}/></span><div><b>Versi baru tersedia</b><small>Muat ulang untuk memakai pembaruan terbaru.</small></div><button type="button" className="pwa-btn" data-testid="pwa-update-button" onClick={applyUpdate}>Muat ulang</button></div>}
      {showInstall && <div className="pwa-card install" data-testid="pwa-install-card">
        <img src="/icons/icon-192.png" alt="" className="pwa-card-logo"/>
        <div className="pwa-card-text"><b>Pasang Ruang Baca di HP-mu</b>
          {installable ? <small>Buka lebih cepat dan lihat katalog yang pernah dibuka walau tanpa internet.</small>
            : <small>Di Safari ketuk <Share size={12}/> <b>Bagikan</b> lalu <b>Tambah ke Layar Utama</b>.</small>}
        </div>
        <div className="pwa-card-actions">
          {installable && <button type="button" className="pwa-btn" data-testid="pwa-install-button" onClick={doInstall}><Download size={14}/> Pasang</button>}
          <button type="button" className="pwa-btn ghost" data-testid="pwa-install-dismiss" onClick={dismissInstall}>Nanti</button>
        </div>
      </div>}
    </div>
  </div>;
}
