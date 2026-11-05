// Mode offline: cache data di IndexedDB, antrean data offline, dan sinkron otomatis saat online lagi.
import { useEffect, useState } from "react";
import { api, isOffline } from "../lib";
import { emit } from "../pwa";
import { idbAll, idbDelete, idbGet, idbPut } from "./idb";

const TOKEN_KEY = "perpus_token";
const SYNC_INTERVAL = 30000;
let queue = [];
let syncing = false;
let lastSync = null;
let rejected = [];
let cachedAt = null;
let started = false;

const uid = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`);
const state = () => ({ online: !isOffline(), queue, syncing, lastSync, rejected, lastDropped: rejected, cachedAt });
const changed = () => emit("perpus:offline-state", state());

// Gagal karena tidak ada koneksi (bukan karena ditolak server)
export const isNetErr = (e) => !e?.response || (e.response.status === 503 && !!e.response.headers?.["x-sw-offline"]);
const errText = (e) => { const d = e?.response?.data?.detail; return typeof d === "string" ? d : Array.isArray(d) ? (d[0]?.msg || "Data tidak valid") : "Ditolak server"; };
const keyOf = (url, params) => { const q = params ? new URLSearchParams(params).toString() : ""; return q ? `${url}?${q}` : url; };

function markCached(at) { if (at) { cachedAt = at; changed(); } }

// GET dengan salinan di IndexedDB: online -> simpan salinan terbaru; offline -> pakai salinan terakhir
export async function cachedGet(url, params) {
  const key = keyOf(url, params);
  try {
    const res = await api.get(url, { params });
    if (res.headers?.["x-sw-cache"] === "hit") {
      const hit = await idbGet("cache", key).catch(() => null);
      const swAt = res.headers["x-sw-cached-at"] || "";
      if (hit && hit.at > swAt) { markCached(hit.at); return hit.data; }
      markCached(swAt || new Date().toISOString());
      return res.data;
    }
    idbPut("cache", { data: res.data, at: new Date().toISOString() }, key).catch(() => {});
    if (cachedAt) { cachedAt = null; changed(); }
    return res.data;
  } catch (e) {
    if (!isNetErr(e)) throw e;
    const hit = await idbGet("cache", key).catch(() => null);
    if (hit) { markCached(hit.at); return hit.data; }
    throw e;
  }
}

// Simpan data sesi saat login -> aplikasi tetap bisa dibuka ulang walau langsung offline
export function rememberSession(user) {
  if (user && typeof user === "object") idbPut("cache", { data: user, at: new Date().toISOString() }, "/auth/me").catch(() => {});
}

export function forgetSession() { idbDelete("cache", "/auth/me").catch(() => {}); }

export async function loadQueue() {
  const rows = await idbAll("queue").catch(() => []);
  queue = rows.sort((a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0));
  changed();
  return queue;
}

// Data yang ditolak server disimpan permanen di perangkat sampai dicoba lagi / dihapus petugas
export async function loadRejected() {
  const rows = await idbAll("rejected").catch(() => []);
  rejected = rows.sort((a, b) => (a.rejected_at < b.rejected_at ? 1 : -1));
  changed();
  return rejected;
}

// kind: tx | visit-scan | visit-guest | visit-checkout
export async function enqueue(kind, payload, meta = {}) {
  const id = uid();
  const created_at = new Date().toISOString();
  const item = { id, kind, payload: { ...payload, client_id: id, client_time: created_at }, created_at, meta };
  await idbPut("queue", item);
  queue = [...queue, item];
  changed();
  return item;
}

function send(item) {
  const p = item.payload;
  if (item.kind === "tx") return api.post("/transactions", p);
  if (item.kind === "visit-scan") return api.post("/visits/scan", p);
  if (item.kind === "visit-guest") return api.post("/visits/guest", p);
  if (item.kind === "visit-checkout") return api.post(`/visits/${encodeURIComponent(p.visit_id)}/checkout`, { client_id: p.client_id, client_time: p.client_time });
  return Promise.reject(Object.assign(new Error("Jenis data tidak dikenal"), { response: { status: 400, data: { detail: "Jenis data tidak dikenal" } } }));
}

export async function syncQueue() {
  if (syncing || isOffline()) return null;
  const items = await loadQueue();
  if (!items.length) return null;
  syncing = true; changed();
  const synced = []; const dropped = [];
  try {
    for (const it of items) {
      try {
        await send(it);
        synced.push(it);
        await idbDelete("queue", it.id).catch(() => {});
      } catch (e) {
        const st = e?.response?.status;
        // Koneksi putus / server bermasalah / sesi login habis -> coba lagi nanti, antrean tetap
        if (isNetErr(e) || st >= 500 || st === 401 || st === 403 || st === 429) break;
        // Ditolak server (mis. stok habis) -> dibuang otomatis + pemberitahuan
        const rej = { ...it, reason: errText(e), rejected_at: new Date().toISOString(), attempts: 1 };
        dropped.push(rej);
        await idbPut("rejected", rej).catch(() => {});
        await idbDelete("queue", it.id).catch(() => {});
      }
    }
  } finally {
    syncing = false;
    if (synced.length || dropped.length) lastSync = new Date().toISOString();
    if (dropped.length) await loadRejected();
    await loadQueue();
    if (synced.length || dropped.length) emit("perpus:sync-done", { synced, dropped });
  }
  return { synced, dropped };
}

export function startOfflineSync() {
  if (started || typeof window === "undefined") return;
  started = true;
  loadRejected();
  loadQueue().then(() => { if (!isOffline()) syncQueue(); });
  window.addEventListener("online", () => { changed(); setTimeout(() => syncQueue(), 1200); });
  window.addEventListener("offline", changed);
  setInterval(() => { if (queue.length && !isOffline() && localStorage.getItem(TOKEN_KEY) !== null) syncQueue(); }, SYNC_INTERVAL);
}

/* ---------- Kelola antrean: batalkan data menunggu, coba lagi / hapus data yang ditolak ---------- */

// Batalkan satu data offline yang belum terkirim (mis. salah input)
export async function cancelQueued(id) {
  if (syncing) return false;
  await idbDelete("queue", id).catch(() => {});
  await loadQueue();
  return true;
}

// Kirim ulang data yang ditolak (mis. stok sudah tersedia lagi). Hasil: { ok, reason?, net? }
export async function retryRejected(id) {
  const it = rejected.find((r) => r.id === id);
  if (!it) return { ok: false, reason: "Data tidak ditemukan" };
  if (isOffline()) return { ok: false, net: true };
  const { reason, rejected_at, attempts, ...item } = it;
  try {
    await send(item);
    await idbDelete("rejected", id).catch(() => {});
    lastSync = new Date().toISOString();
    await loadRejected();
    emit("perpus:sync-done", { synced: [item], dropped: [], retried: true });
    return { ok: true };
  } catch (e) {
    if (isNetErr(e) || e?.response?.status >= 500) return { ok: false, net: true };
    const upd = { ...it, reason: errText(e), rejected_at: new Date().toISOString(), attempts: (attempts || 1) + 1 };
    await idbPut("rejected", upd).catch(() => {});
    await loadRejected();
    return { ok: false, reason: upd.reason };
  }
}

export async function deleteRejected(ids) {
  for (const id of [].concat(ids)) await idbDelete("rejected", id).catch(() => {});
  await loadRejected();
}

export const clearDropped = () => deleteRejected(rejected.map((r) => r.id));

export function useOffline() {
  const [s, setS] = useState(state);
  useEffect(() => {
    const on = () => setS(state());
    window.addEventListener("perpus:offline-state", on);
    window.addEventListener("online", on); window.addEventListener("offline", on);
    on();
    return () => { window.removeEventListener("perpus:offline-state", on); window.removeEventListener("online", on); window.removeEventListener("offline", on); };
  }, []);
  return { ...s, sync: syncQueue, cancelQueued, retryRejected, deleteRejected };
}

/* ---------- Data offline ditampilkan di atas data tersimpan (belum ada di server) ---------- */

const bookStatus = (b) => (b.available > 0 ? "Tersedia" : b.borrowed > 0 ? "Dipinjam" : b.lost > 0 ? "Hilang" : "Habis");

export function applyPendingStaff(raw, items) {
  const tx = items.filter((q) => q.kind === "tx");
  if (!tx.length) return raw;
  const books = raw.books.map((b) => ({ ...b }));
  const byId = Object.fromEntries(books.map((b) => [b.id, b]));
  const transactions = [...(raw.transactions || [])];
  const loans = [...(raw.reports?.loans || [])];
  let dBorrow = 0;
  for (const q of tx) {
    const { member_id, book_id, action } = q.payload; const m = q.meta || {};
    const b = byId[book_id];
    if (b) {
      if (action === "pinjam") { b.available = Math.max(0, (b.available || 0) - 1); b.borrowed = (b.borrowed || 0) + 1; }
      else { b.available = Math.min(b.stock || 0, (b.available || 0) + 1); b.borrowed = Math.max(0, (b.borrowed || 0) - 1); }
      b.status = bookStatus(b);
    }
    dBorrow += action === "pinjam" ? 1 : -1;
    const rec = { id: `local-${q.id}`, member_id, member_name: m.member_name, class_name: m.class_name || "", book_id, book_title: m.book_title, action, date: q.created_at, pending: true };
    transactions.unshift(rec);
    if (action === "pinjam") loans.unshift({ ...rec, borrowed_at: q.created_at, returned_at: null, status: "Dipinjam" });
    else {
      const i = loans.findIndex((l) => l.member_id === member_id && l.book_id === book_id && l.status === "Dipinjam");
      if (i >= 0) loans[i] = { ...loans[i], status: "Dikembalikan", returned_at: q.created_at, pending: true };
    }
  }
  const stats = raw.stats ? { ...raw.stats, borrowed: Math.max(0, (raw.stats.borrowed || 0) + dBorrow), available: Math.max(0, (raw.stats.available || 0) - dBorrow) } : raw.stats;
  return { ...raw, books, transactions, stats, reports: { ...(raw.reports || {}), loans } };
}

const wibDate = (iso) => new Date(new Date(iso).getTime() + 7 * 3600 * 1000).toISOString().slice(0, 10);
const minutes = (a, b) => Math.max(0, Math.floor((new Date(b) - new Date(a)) / 60000));

// day = "YYYY-MM-DD" (halaman Pengunjung) atau null (laporan: semua tanggal)
export function applyPendingVisits(list, items, day = null) {
  const visits = items.filter((q) => q.kind.startsWith("visit-") && (!day || wibDate(q.created_at) === day));
  if (!visits.length) return list;
  const rows = [...list];
  for (const q of visits) {
    const p = q.payload; const m = q.meta || {};
    if (q.kind === "visit-scan") {
      const i = rows.findIndex((v) => v.member_id === m.member_id && !v.check_out);
      if (m.action === "keluar" && i >= 0) rows[i] = { ...rows[i], check_out: q.created_at, checkout_type: "scan", duration_min: minutes(rows[i].check_in, q.created_at), pending: true };
      else if (i < 0) rows.unshift({ id: `local-${q.id}`, kind: "anggota", member_id: m.member_id, student_id: m.student_id || "", name: m.name, class_name: m.class_name || "", purpose: p.purpose || "", origin: "", photo: m.photo || "", check_in: q.created_at, check_out: null, checkout_type: null, duration_min: null, date: wibDate(q.created_at), pending: true });
    } else if (q.kind === "visit-guest") {
      rows.unshift({ id: `local-${q.id}`, kind: "tamu", member_id: null, student_id: "", name: p.name, class_name: "Tamu", purpose: p.purpose || "", origin: p.origin || "", photo: "", check_in: q.created_at, check_out: null, checkout_type: null, duration_min: null, date: wibDate(q.created_at), pending: true });
    } else if (q.kind === "visit-checkout") {
      const i = rows.findIndex((v) => v.id === p.visit_id);
      if (i >= 0) rows[i] = { ...rows[i], check_out: q.created_at, checkout_type: "manual", duration_min: minutes(rows[i].check_in, q.created_at), pending: true };
    }
  }
  return rows.sort((a, b) => (a.check_in < b.check_in ? 1 : -1));
}

export function applyPendingVisitDay(data, items) {
  const list = applyPendingVisits(data.items || [], items, data.date);
  if (list === data.items) return data;
  return { ...data, items: list, summary: { total: list.length, inside: list.filter((v) => !v.check_out).length, anggota: list.filter((v) => v.kind === "anggota").length, tamu: list.filter((v) => v.kind === "tamu").length } };
}
