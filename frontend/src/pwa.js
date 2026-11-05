// Pendaftaran service worker + utilitas PWA (cache, install, status offline)
import { idbClear } from "./lib/idb";
const API_CACHE_PREFIX = "perpus-api-";
const TOKEN_KEY = "perpus_token";
const WARM_API = /^\/api\/(auth\/me|books|shelves|settings(\/student-photo)?|dashboard|members(\/options)?|transactions|reports(\/summary)?|overdue|reservations(\/mine)?|stocktake|incoming|visits(\/(config|stats|leaderboard|history))?|loans\/leaderboard|account\/(member|history))$/;

export const emit = (name, detail) => { try { window.dispatchEvent(new CustomEvent(name, { detail })); } catch { /* */ } };

export function clearApiCache() {
  // Salinan data offline (IndexedDB) ikut dibersihkan; antrean data offline TIDAK dihapus agar tetap tersinkron
  idbClear("cache").catch(() => {});
  try {
    navigator.serviceWorker?.controller?.postMessage({ type: "CLEAR_API_CACHE" });
    if (typeof caches !== "undefined") {
      return caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith(API_CACHE_PREFIX)).map((k) => caches.delete(k)))).catch(() => {});
    }
  } catch { /* */ }
  return Promise.resolve();
}

function warmCaches() {
  try {
    const entries = performance.getEntriesByType("resource").map((e) => e.name);
    const origin = window.location.origin;
    const statics = entries.filter((u) => (u.startsWith(origin) && !u.includes("/api/") && !u.includes("/__")) || /^https:\/\/fonts\.(googleapis|gstatic)\.com\//.test(u));
    navigator.serviceWorker.controller?.postMessage({ type: "WARM", urls: [...new Set(statics)] });
    // Ulangi permintaan data yang dimuat sebelum service worker aktif agar ikut tersimpan
    const token = localStorage.getItem(TOKEN_KEY);
    const apiUrls = [...new Set(entries.filter((u) => { try { const p = new URL(u); return WARM_API.test(p.pathname); } catch { return false; } }))];
    apiUrls.slice(0, 25).forEach((u) => {
      fetch(u, { credentials: "include", headers: token ? { Authorization: `Bearer ${token}` } : {} }).catch(() => {});
    });
  } catch { /* */ }
}

let waitingWorker = null;
export function applyUpdate() {
  window.__perpusSwReload = true;
  if (waitingWorker) waitingWorker.postMessage({ type: "SKIP_WAITING" });
  else window.location.reload();
}

export function registerServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator) || !window.isSecureContext) return;
  const start = async () => {
    try {
      const hadController = !!navigator.serviceWorker.controller;
      const reg = await navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
      const onWaiting = (w) => { waitingWorker = w; emit("perpus:sw-update"); };
      if (reg.waiting && navigator.serviceWorker.controller) onWaiting(reg.waiting);
      reg.addEventListener("updatefound", () => {
        const w = reg.installing;
        if (!w) return;
        w.addEventListener("statechange", () => { if (w.state === "installed" && navigator.serviceWorker.controller) onWaiting(w); });
      });
      let reloading = false;
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (!hadController) { emit("perpus:sw-ready"); warmCaches(); return; }
        if (window.__perpusSwReload && !reloading) { reloading = true; window.location.reload(); }
      });
      if (hadController) emit("perpus:sw-ready");
      setInterval(() => reg.update().catch(() => {}), 60 * 60 * 1000);
    } catch (e) {
      console.warn("Service worker gagal didaftarkan:", e);
    }
  };
  if (document.readyState === "complete") start(); else window.addEventListener("load", start, { once: true });
}

// ---- Install prompt (Android/desktop Chrome & Edge) ----
let deferredPrompt = null;
if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferredPrompt = e; emit("perpus:installable", true); });
  window.addEventListener("appinstalled", () => { deferredPrompt = null; emit("perpus:installable", false); emit("perpus:installed"); });
}
export const canPromptInstall = () => !!deferredPrompt;
export async function promptInstall() {
  if (!deferredPrompt) return "unavailable";
  const ev = deferredPrompt; deferredPrompt = null;
  ev.prompt();
  const choice = await ev.userChoice.catch(() => ({ outcome: "dismissed" }));
  emit("perpus:installable", false);
  return choice?.outcome || "dismissed";
}
export const isStandalone = () => (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || window.navigator.standalone === true;
export const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
