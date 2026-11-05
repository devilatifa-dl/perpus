import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Camera, CameraOff, CheckCircle2, Clock, DoorClosed, DoorOpen, Keyboard, LogIn, LogOut, Maximize2, Pencil, ScanLine, Search, Trash2, UserPlus, Users, X } from "lucide-react";
import { api, isOffline } from "../lib";
import { applyPendingVisitDay, cachedGet, enqueue, isNetErr, useOffline } from "../lib/offline";
import { OfflineBar, PendingTag } from "./OfflineBar";
import { ShowMore } from "../lib/showMore";
import { Modal } from "./Shared";
import { beep, cameraError, createCamera, unlockAudio } from "../lib/camera";

const COOLDOWN_MS = 1000;

const todayStr = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);
export const fmtClock = (d) => d ? new Date(d).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }) : "-";
export const fmtDur = (m) => m == null ? "-" : m >= 60 ? `${Math.floor(m / 60)} j ${m % 60} m` : `${m} menit`;
export const OUT_LABEL = { scan: "Scan keluar", manual: "Dicatat petugas", otomatis: "Otomatis" };
// Keperluan kunjungan: dipilih sebelum scan masuk (anggota) atau di form tamu. Ikut tampil di laporan Pengunjung.
export const VISIT_PURPOSES = ["Membaca", "Meminjam / mengembalikan buku", "Mengerjakan tugas", "Lainnya"];
export const GUEST_PURPOSES = ["Membaca", "Meminjam / mengembalikan buku", "Mengerjakan tugas", "Kunjungan dinas", "Lainnya"];
const PURPOSE_KEY = "perpus-visit-purpose";
const OTHER_KEY = "perpus-visit-purpose-other";
const OTHER = "Lainnya";
const loadOther = () => { try { return localStorage.getItem(OTHER_KEY) || ""; } catch { return ""; } };
// "Lainnya" + teks ketikan petugas -> teks itu yang disimpan (kosong = "Lainnya")
export const resolvePurpose = (choice, other) => (choice === OTHER ? (other || "").trim().slice(0, 120) || OTHER : choice);
const loadPurpose = () => { try { const v = localStorage.getItem(PURPOSE_KEY); return VISIT_PURPOSES.includes(v) ? v : "Membaca"; } catch { return "Membaca"; } };
const slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

const OVERLAY = {
  masuk: { tone: "ok", label: "BERHASIL · MASUK", Icon: CheckCircle2 },
  keluar: { tone: "ok", label: "BERHASIL · KELUAR", Icon: CheckCircle2 },
  sudah_masuk: { tone: "warn", label: "SUDAH TERCATAT MASUK", Icon: Clock },
  sudah_keluar: { tone: "warn", label: "SUDAH TERCATAT KELUAR", Icon: Clock },
  error: { tone: "bad", label: "GAGAL", Icon: AlertTriangle },
};

function LiveScanner({ onCode }) {
  const [err, setErr] = useState(""); const [ready, setReady] = useState(false); const [hit, setHit] = useState(null);
  const lock = useRef(false); const last = useRef({ code: "", at: 0 }); const cb = useRef(onCode); const timer = useRef(null); const boxRef = useRef(null);
  cb.current = onCode;
  useEffect(() => {
    let alive = true; let cam = null;
    const onDecode = async (text) => {
      const now = Date.now();
      // Kartu yang sama masih di depan kamera: abaikan sebentar agar tidak langsung tercatat keluar
      if (lock.current || (text === last.current.code && now - last.current.at < 5000)) return;
      lock.current = true; last.current = { code: text, at: now };
      let r;
      try { r = await cb.current(text); } catch (e) { r = null; }
      if (!alive) return;
      setHit(r || { action: "error", message: "Gagal memproses kode" });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => { if (!alive) return; setHit(null); lock.current = false; last.current.at = Date.now(); }, COOLDOWN_MS);
    };
    // Ditunda sedikit agar kamera hanya dibuka sekali (React dev memasang komponen dua kali)
    const t = setTimeout(() => {
      if (!alive || !boxRef.current) return;
      cam = createCamera(boxRef.current);
      cam.start(onDecode).then(() => alive && setReady(true)).catch((e) => alive && setErr(cameraError(e)));
    }, 60);
    return () => { alive = false; clearTimeout(t); clearTimeout(timer.current); cam?.stop(); };
  }, []);
  const o = hit ? (OVERLAY[hit.action] || OVERLAY.error) : null;
  return <div className="visit-cam" data-testid="visit-camera">
    <div className="visit-cam-frame">
      <div ref={boxRef} className="visit-qr-reader"/>
      {o && <div className={`visit-cam-hit ${o.tone}`} data-testid="visit-camera-hit">
        <o.Icon size={46}/>
        <small>{o.label}</small>
        <b>{hit.member?.name || hit.message}</b>
        <span>{o.tone === "bad" ? "Periksa kartu lalu scan lagi" : `${hit.member?.class_name || "Tamu"}${hit.action === "masuk" && hit.visit?.purpose ? ` · ${hit.visit.purpose}` : ""}`}</span>
        <i className="visit-cam-bar" style={{ animationDuration: `${COOLDOWN_MS}ms` }}/>
      </div>}
    </div>
    {!err && <div className={`visit-cam-status ${hit ? "wait" : ready ? "ready" : ""}`} data-testid="visit-camera-status">
      <span className="dot"/>{!ready ? "Membuka kamera..." : hit ? "Tunggu sebentar..." : "Siap scan — arahkan QR kartu ke kotak"}
    </div>}
    {err && <div className="error" data-testid="visit-camera-error">{err}</div>}
  </div>;
}

function MemberSuggest({ items, active, onPick }) {
  if (!items.length) return null;
  return <ul className="visit-suggest" data-testid="visit-suggest" role="listbox">
    {items.map((m, i) => <li key={m.id}>
      <button type="button" role="option" aria-selected={i === active} className={i === active ? "active" : ""} data-testid={`visit-suggest-${m.id}`} onMouseDown={(e) => e.preventDefault()} onClick={() => onPick(m)}>
        <div className="avatar">{m.photo ? <img src={m.photo} alt={m.name}/> : (m.name || "?")[0]}</div>
        <div className="visit-suggest-text"><b>{m.name}</b><span>{m.class_name || "-"} · NIS {m.student_id || m.id}</span></div>
        <em className={m.inside ? "out" : "in"}>{m.inside ? <><LogOut size={13}/> Catat keluar</> : <><LogIn size={13}/> Catat masuk</>}</em>
      </button>
    </li>)}
  </ul>;
}

const NEED_ONLINE = "Butuh koneksi internet — coba lagi setelah online";

export function Visitors({ notify, members = [] }) {
  const [date, setDate] = useState(todayStr()); const [rawData, setData] = useState({ date: todayStr(), items: [], summary: { total: 0, inside: 0, anggota: 0, tamu: 0 }, checkout_time: "14:00" });
  // Catatan offline (belum tersinkron) ditampilkan bersama data tersimpan
  const { queue } = useOffline(); const data = useMemo(() => applyPendingVisitDay(rawData, queue), [rawData, queue]);
  const dataRef = useRef(data); dataRef.current = data; const membersRef = useRef(members); membersRef.current = members;
  const [code, setCode] = useState(""); const [busy, setBusy] = useState(false); const [result, setResult] = useState(null);
  const [camOn, setCamOn] = useState(false); const [guest, setGuest] = useState(false); const [guestForm, setGuestForm] = useState({ name: "", origin: "", purpose: "Membaca" });
  const [filter, setFilter] = useState("semua"); const [cfgOpen, setCfgOpen] = useState(false); const [cfgTime, setCfgTime] = useState("14:00");
  const [q, setQ] = useState(""); const [sugs, setSugs] = useState([]); const [sugActive, setSugActive] = useState(-1);
  const [purpose, setPurposeState] = useState(loadPurpose); const purposeRef = useRef(purpose); purposeRef.current = purpose;
  const setPurpose = (v) => { setPurposeState(v); try { localStorage.setItem(PURPOSE_KEY, v); } catch { /* abaikan */ } };
  const [other, setOtherState] = useState(loadOther); const otherRef = useRef(other); otherRef.current = other;
  const setOther = (v) => { setOtherState(v); try { localStorage.setItem(OTHER_KEY, v); } catch { /* abaikan */ } };
  const [guestOther, setGuestOther] = useState("");
  const [purposeEdit, setPurposeEdit] = useState(null);
  // Keyboard layar HP tidak langsung muncul: kolom tetap fokus untuk alat pemindai (inputMode "none"),
  // keyboard baru tampil setelah petugas menekan tombol keyboard.
  const [kbOn, setKbOn] = useState(false);
  const kbOpening = useRef(false);
  const openKeyboard = () => { setKbOn(true); const el = inputRef.current; if (!el) return; kbOpening.current = true; el.blur(); setTimeout(() => { el.focus(); kbOpening.current = false; }, 60); };
  const inputRef = useRef(null); const kioskRef = useRef(null); const resultTimer = useRef(null); const camOnRef = useRef(false); const busyRef = useRef(false);
  camOnRef.current = camOn;
  const isToday = date === todayStr();
  const notifyRef = useRef(notify); notifyRef.current = notify;
  const load = useCallback(() => cachedGet("/visits", { date }).then((d) => setData({ ...d, date: d.date || date })).catch(() => { if (isOffline()) setData((x) => ({ ...x, date, items: x.date === date ? x.items : [] })); else notifyRef.current("Data pengunjung belum dapat dimuat"); }), [date]);
  // Pencarian nama saat offline memakai daftar anggota yang tersimpan di perangkat
  const localSearch = (term) => {
    const t = term.toLowerCase();
    const inside = new Set(dataRef.current.items.filter((v) => !v.check_out && v.member_id).map((v) => v.member_id));
    return membersRef.current.filter((m) => [m.name, m.student_id, m.id, m.class_name].some((x) => (x || "").toLowerCase().includes(t)))
      .sort((a, b) => (!(a.name || "").toLowerCase().startsWith(t)) - (!(b.name || "").toLowerCase().startsWith(t)) || (a.name || "").localeCompare(b.name || ""))
      .slice(0, 8).map((m) => ({ ...m, inside: inside.has(m.id) }));
  };
  // Scan saat offline: masuk/keluar ditentukan dari data tersimpan, lalu disimpan di antrean perangkat
  const scanOffline = async (c) => {
    const t = c.toLowerCase();
    const m = membersRef.current.find((x) => (x.id || "").toLowerCase() === t || (x.student_id || "").toLowerCase() === t);
    if (!m) return { action: "error", message: "Kode kartu tidak ditemukan di data tersimpan (offline)" };
    const open = dataRef.current.items.find((v) => v.member_id === m.id && !v.check_out);
    if (open && Date.now() - new Date(open.check_in).getTime() < 30000) return { action: "sudah_masuk", visit: open, member: m, offline: true };
    const action = open ? "keluar" : "masuk"; const purposeText = resolvePurpose(purposeRef.current, otherRef.current); const now = new Date().toISOString();
    await enqueue("visit-scan", { code: m.id, purpose: purposeText }, { label: `${m.name} ${action}`, action, member_id: m.id, student_id: m.student_id, name: m.name, class_name: m.class_name, photo: m.photo });
    return { action, member: m, offline: true, visit: action === "masuk" ? { check_in: now, purpose: purposeText } : { ...open, check_out: now, duration_min: Math.max(0, Math.floor((Date.now() - new Date(open.check_in).getTime()) / 60000)) } };
  };
  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t); }, [load]);
  // Setelah data offline tersinkron, muat ulang daftar dari server
  useEffect(() => { const h = () => load(); window.addEventListener("perpus:sync-done", h); return () => window.removeEventListener("perpus:sync-done", h); }, [load]);
  useEffect(() => { if (isToday && !camOnRef.current) inputRef.current?.focus(); }, [isToday]);
  // Saran nama anggota saat mengetik di kolom pencarian
  useEffect(() => {
    const term = code.trim();
    if (term.length < 2) { setSugs([]); setSugActive(-1); return undefined; }
    let live = true;
    const t = setTimeout(() => {
      if (isOffline()) { if (live) { setSugs(localSearch(term)); setSugActive(-1); } return; }
      api.get("/visits/member-search", { params: { q: term } }).then((r) => { if (live) { setSugs(r.data); setSugActive(-1); } }).catch((e) => live && setSugs(isNetErr(e) ? localSearch(term) : []));
    }, 200);
    return () => { live = false; clearTimeout(t); };
  }, [code]);
  const flash = (r) => { setResult(r); clearTimeout(resultTimer.current); resultTimer.current = setTimeout(() => setResult(null), 6000); };
  const submitCode = async (raw) => {
    const c = (raw || "").trim(); if (!c || busyRef.current) return null;
    busyRef.current = true; setBusy(true);
    let out = null;
    const offlineScan = async () => { let r; try { r = await scanOffline(c); } catch (err) { r = { action: "error", message: "Gagal menyimpan data offline di perangkat" }; } beep(r.action === "masuk" || r.action === "keluar"); flash(r); return r; };
    try {
      if (isOffline()) out = await offlineScan();
      else {
        const { data: r } = await api.post("/visits/scan", { code: c, purpose: resolvePurpose(purposeRef.current, otherRef.current) });
        beep(r.action === "masuk" || r.action === "keluar"); flash(r); load(); out = r;
      }
    } catch (e) {
      if (isNetErr(e)) out = await offlineScan();
      else { beep(false); out = { action: "error", message: e.response?.data?.detail || "Gagal memproses kode" }; flash(out); }
    }
    finally {
      busyRef.current = false; setBusy(false); setCode(""); setSugs([]); setSugActive(-1); setKbOn(false);
      // Di HP jangan fokus ke kolom ketik saat kamera aktif (keyboard akan menutupi kamera)
      if (!camOnRef.current) inputRef.current?.focus();
    }
    return out;
  };
  const pickMember = (m) => submitCode(m.id);
  const onSearchSubmit = (e) => {
    e.preventDefault();
    if (sugActive >= 0 && sugs[sugActive]) return pickMember(sugs[sugActive]);
    const t = code.trim().toLowerCase();
    const exact = sugs.find((m) => (m.id || "").toLowerCase() === t || (m.student_id || "").toLowerCase() === t);
    if (!exact && sugs.length === 1) return pickMember(sugs[0]);
    return submitCode(code);
  };
  const onSearchKey = (e) => {
    if (!sugs.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setSugActive((i) => (i + 1) % sugs.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSugActive((i) => (i <= 0 ? sugs.length - 1 : i - 1)); }
    else if (e.key === "Escape") { e.stopPropagation(); setSugs([]); setSugActive(-1); }
  };
  const addGuest = async (e) => {
    e.preventDefault();
    const body = { ...guestForm, name: guestForm.name.trim(), purpose: resolvePurpose(guestForm.purpose, guestOther) };
    const done = (v, offline) => { setGuest(false); setGuestForm({ name: "", origin: "", purpose: "Membaca" }); setGuestOther(""); flash({ action: "masuk", visit: v, offline, member: { name: v.name, class_name: v.origin || "Tamu" } }); };
    const offlineGuest = async () => { try { await enqueue("visit-guest", body, { label: `Tamu ${body.name}` }); done({ ...body, check_in: new Date().toISOString() }, true); } catch (e2) { notify("Gagal menyimpan data offline di perangkat"); } };
    if (isOffline()) return offlineGuest();
    try { const { data: v } = await api.post("/visits/guest", body); done(v, false); load(); }
    catch (err) { if (isNetErr(err)) return offlineGuest(); notify(err.response?.data?.detail || "Gagal mencatat tamu"); }
  };
  const changePurpose = async (v, value) => { if (v.pending || isOffline()) return notify(NEED_ONLINE); try { await api.patch(`/visits/${v.id}/purpose`, { purpose: value }); notify(`Keperluan ${v.name}: ${value || "-"}`); load(); } catch (e) { notify(e.response?.data?.detail || "Gagal mengubah keperluan"); } };
  const checkoutOffline = async (v) => {
    try {
      if (v.pending && v.kind === "anggota") await enqueue("visit-scan", { code: v.member_id, purpose: "" }, { label: `${v.name} keluar`, action: "keluar", member_id: v.member_id, student_id: v.student_id, name: v.name, class_name: v.class_name, photo: v.photo });
      else await enqueue("visit-checkout", { visit_id: v.id }, { label: `${v.name} keluar` });
      notify(`Offline · ${v.name} tercatat keluar, akan disinkronkan otomatis`);
    } catch (e) { notify("Gagal menyimpan data offline di perangkat"); }
  };
  const checkout = async (v) => {
    if (v.pending && v.kind === "tamu") return notify("Tamu ini dicatat saat offline. Catat keluar setelah tersinkron, atau otomatis keluar pada jam pulang.");
    if (v.pending || isOffline()) return checkoutOffline(v);
    try { await api.post(`/visits/${v.id}/checkout`); notify(`${v.name} tercatat keluar`); load(); } catch (e) { if (isNetErr(e)) return checkoutOffline(v); notify(e.response?.data?.detail || "Gagal"); }
  };
  const remove = async (v) => { if (v.pending || isOffline()) return notify(NEED_ONLINE); if (!window.confirm(`Hapus catatan pengunjung ${v.name}?`)) return; try { await api.delete(`/visits/${v.id}`); notify("Catatan pengunjung dihapus"); load(); } catch (e) { notify("Gagal menghapus"); } };
  const saveCfg = async (e) => { e.preventDefault(); try { const { data: r } = await api.put("/visits/config", { checkout_time: cfgTime }); setCfgOpen(false); notify(`Otomatis keluar diatur pukul ${r.checkout_time} WIB`); load(); } catch (err) { notify("Format jam tidak valid"); } };
  const fullscreen = () => { const el = kioskRef.current; if (!el) return; if (document.fullscreenElement) document.exitFullscreen(); else el.requestFullscreen?.(); };
  const term = q.trim().toLowerCase();
  const rows = data.items.filter((v) => filter === "semua" || (filter === "dalam" ? !v.check_out : !!v.check_out))
    .filter((v) => !term || [v.name, v.class_name, v.origin, v.student_id, v.member_id, v.purpose].some((x) => (x || "").toLowerCase().includes(term)));
  const s = data.summary;
  const res = result;
  return <div className="visitors-page" data-testid="visitors-page">
    <OfflineBar testId="offline-bar-visitors" kinds={["visit-"]}/>
    <div className="visit-top">
      <section className="panel visit-kiosk" ref={kioskRef} data-testid="visit-kiosk">
        <div className="panel-title"><div><p className="eyebrow">BUKU TAMU DIGITAL</p><h3>Scan kartu saat masuk &amp; keluar</h3></div><button className="icon-button" title="Layar penuh" data-testid="visit-fullscreen-button" onClick={fullscreen}><Maximize2 size={17}/></button></div>
        <div className="visit-kiosk-body">
          <div className="visit-scan-area">
            {camOn ? <LiveScanner onCode={submitCode}/> : <div className="visit-scan-idle"><ScanLine size={44}/><b>Siap memindai</b><span>Arahkan alat pemindai QR ke kartu anggota, atau nyalakan kamera.</span></div>}
            <button className={camOn ? "secondary full" : "primary full"} data-testid="visit-camera-toggle" onClick={() => { unlockAudio(); setCamOn(!camOn); }} disabled={!isToday}>{camOn ? <><CameraOff size={16}/> Matikan kamera</> : <><Camera size={16}/> Nyalakan kamera</>}</button>
          </div>
          <div className="visit-scan-side">
            <div className="visit-purpose" data-testid="visit-purpose-picker">
              <span className="visit-purpose-label">Keperluan masuk <small>berlaku untuk setiap scan masuk</small></span>
              <div className="visit-purpose-chips" role="radiogroup" aria-label="Keperluan kunjungan">{VISIT_PURPOSES.map((p) => <button key={p} type="button" role="radio" aria-checked={purpose === p} data-testid={`visit-purpose-${slug(p)}`} className={purpose === p ? "active" : ""} onClick={() => setPurpose(p)} disabled={!isToday}>{p}</button>)}</div>
              {purpose === OTHER && <input className="visit-purpose-other" data-testid="visit-purpose-other-input" maxLength={120} placeholder="Tulis keperluan, mis. Rapat OSIS, Latihan lomba..." value={other} onChange={(e) => setOther(e.target.value)} disabled={!isToday} autoComplete="off"/>}
            </div>
            <form className="visit-code-form" onSubmit={onSearchSubmit} autoComplete="off">
              <div className="visit-search-wrap">
                <label>Nama siswa / kode kartu / NIS<div className="visit-search-input"><Search size={16}/><input ref={inputRef} data-testid="visit-code-input" data-keyboard={kbOn ? "on" : "off"} inputMode={kbOn ? "text" : "none"} placeholder={kbOn ? "Ketik nama, kode kartu, atau NIS" : "Scan kartu / ketuk ikon keyboard"} value={code} onChange={(e) => setCode(e.target.value)} onKeyDown={onSearchKey} onBlur={() => { setTimeout(() => setSugs([]), 150); if (!code && !kbOpening.current) setKbOn(false); }} disabled={!isToday} autoComplete="off"/>{code && <button type="button" className="visit-search-clear" aria-label="Hapus" data-testid="visit-code-clear" onClick={() => { setCode(""); inputRef.current?.focus(); }}><X size={14}/></button>}<button type="button" className={`visit-kb-toggle${kbOn ? " on" : ""}`} aria-label={kbOn ? "Tutup keyboard" : "Buka keyboard untuk mengetik"} aria-pressed={kbOn} title={kbOn ? "Tutup keyboard" : "Ketik manual"} data-testid="visit-keyboard-toggle" disabled={!isToday} onMouseDown={(e) => e.preventDefault()} onClick={() => { if (kbOn) { setKbOn(false); inputRef.current?.blur(); } else openKeyboard(); }}><Keyboard size={16}/></button></div></label>
                <MemberSuggest items={sugs} active={sugActive} onPick={pickMember}/>
              </div>
              <button className="primary" data-testid="visit-code-submit" disabled={busy || !isToday}><LogIn size={16}/> {busy ? "Memproses..." : "Catat"}</button>
            </form>
            <div className={`visit-result ${res ? res.action : "idle"}`} data-testid="visit-result" aria-live="polite">
              {!res && <><Users size={22}/><div><b>Scan pertama = masuk, scan berikutnya = keluar</b><span>Yang lupa scan keluar otomatis tercatat keluar pukul {data.checkout_time} WIB.</span></div></>}
              {res?.action === "masuk" && <><DoorOpen size={26}/><div><small>MASUK · {fmtClock(res.visit?.check_in)}</small><b data-testid="visit-result-name">{res.member?.name}</b><span>Selamat datang{res.member?.class_name ? ` · ${res.member.class_name}` : ""}{res.visit?.purpose ? <> · <em data-testid="visit-result-purpose">{res.visit.purpose}</em></> : ""}</span>{res.offline && <i className="offline-note" data-testid="visit-result-offline">Tersimpan offline · sinkron otomatis</i>}</div></>}
              {res?.action === "keluar" && <><DoorClosed size={26}/><div><small>KELUAR · {fmtClock(res.visit?.check_out)}</small><b data-testid="visit-result-name">{res.member?.name}</b><span>Sampai jumpa · lama berkunjung {fmtDur(res.visit?.duration_min)}</span>{res.offline && <i className="offline-note" data-testid="visit-result-offline">Tersimpan offline · sinkron otomatis</i>}</div></>}
              {(res?.action === "sudah_masuk" || res?.action === "sudah_keluar") && <><Clock size={24}/><div><small>BARU SAJA DIPINDAI</small><b data-testid="visit-result-name">{res.member?.name}</b><span>{res.action === "sudah_masuk" ? "Sudah tercatat masuk. Scan lagi saat keluar." : "Sudah tercatat keluar."}</span></div></>}
              {res?.action === "error" && <><ScanLine size={24}/><div><small>GAGAL</small><b data-testid="visit-result-name">{res.message}</b><span>Periksa kartu atau catat sebagai tamu.</span></div></>}
            </div>
            <button className="secondary full" data-testid="visit-guest-button" onClick={() => setGuest(true)} disabled={!isToday}><UserPlus size={16}/> Catat tamu (tanpa kartu)</button>
          </div>
        </div>
      </section>
      <aside className="visit-stats">
        <div className="visit-stat big" data-testid="visit-inside"><span>Di dalam sekarang</span><strong>{s.inside}</strong><small>pengunjung</small></div>
        <div className="visit-stat" data-testid="visit-total"><span>{isToday ? "Total hari ini" : "Total tanggal ini"}</span><strong>{s.total}</strong></div>
        <div className="visit-stat"><span>Anggota</span><strong data-testid="visit-members-count">{s.anggota}</strong><small>{s.total ? Math.round((s.anggota / s.total) * 100) : 0}%</small></div>
        <div className="visit-stat"><span>Tamu</span><strong data-testid="visit-guests-count">{s.tamu}</strong><small>{s.total ? Math.round((s.tamu / s.total) * 100) : 0}%</small></div>
        <button className="visit-auto" data-testid="visit-config-button" onClick={() => { setCfgTime(data.checkout_time); setCfgOpen(true); }}><Clock size={16}/><div><b>Otomatis keluar {data.checkout_time} WIB</b><small>Ubah jam pulang sekolah</small></div><Pencil size={14}/></button>
      </aside>
    </div>
    <div className="panel table-panel">
      <div className="panel-title visit-list-head"><div><p className="eyebrow">DAFTAR PENGUNJUNG</p><h3>{rows.length} catatan</h3></div>
        <div className="visit-filters">
          <div className="visit-list-search"><Search size={15}/><input data-testid="visit-list-search" placeholder="Cari nama pengunjung..." value={q} onChange={(e) => setQ(e.target.value)}/>{q && <button type="button" aria-label="Hapus pencarian" data-testid="visit-list-search-clear" onClick={() => setQ("")}><X size={13}/></button>}</div>
          <div className="period-select">{[["semua", "Semua"], ["dalam", "Di dalam"], ["keluar", "Sudah keluar"]].map(([k, l]) => <button key={k} data-testid={`visit-filter-${k}`} className={filter === k ? "active" : ""} onClick={() => setFilter(k)}>{l}</button>)}</div>
          <input type="date" data-testid="visit-date-input" value={date} max={todayStr()} onChange={(e) => setDate(e.target.value || todayStr())}/>
        </div>
      </div>
      <div className="table-wrap"><table><thead><tr><th>PENGUNJUNG</th><th>KELAS / ASAL</th><th>KEPERLUAN</th><th>MASUK</th><th>KELUAR</th><th>DURASI</th><th>STATUS</th><th></th></tr></thead><tbody>
        <ShowMore items={rows} colSpan={8}>{(vis) => vis.map((v) => <tr key={v.id} data-testid={`visit-row-${v.id}`} className={v.pending ? "row-pending" : undefined}>
          <td><div className="book-cell"><div className={`avatar ${v.kind === "tamu" ? "guest" : ""}`}>{v.photo ? <img src={v.photo} alt={v.name}/> : v.name[0]}</div><div><b>{v.name}</b>{v.pending && <PendingTag testId={`visit-pending-${v.id}`}/>}<span>{v.kind === "tamu" ? "Tamu" : `Anggota · ${v.student_id || v.member_id}`}</span></div></div></td>
          <td>{v.kind === "tamu" ? (v.origin || "-") : v.class_name}</td>
          <td><select className="visit-purpose-select" aria-label={`Keperluan ${v.name}`} data-testid={`visit-purpose-select-${v.id}`} value={v.purpose || ""} onChange={(e) => { const val = e.target.value; if (val === "__other") setPurposeEdit({ visit: v, text: GUEST_PURPOSES.includes(v.purpose) ? "" : (v.purpose || "") }); else changePurpose(v, val); }}><option value="">— Belum diisi —</option>{[...new Set([...GUEST_PURPOSES, ...(v.purpose ? [v.purpose] : [])])].map((p) => <option key={p} value={p}>{p}</option>)}<option value="__other">Tulis sendiri...</option></select></td>
          <td>{fmtClock(v.check_in)}</td>
          <td>{v.check_out ? fmtClock(v.check_out) : "-"}</td>
          <td>{fmtDur(v.duration_min)}</td>
          <td>{v.check_out ? <span className={`status ${v.checkout_type === "otomatis" ? "dipinjam" : "keluar"}`}>{OUT_LABEL[v.checkout_type] || "Keluar"}</span> : <span className="status tersedia" data-testid={`visit-inside-${v.id}`}>Di dalam</span>}</td>
          <td><div className="row-actions">{!v.check_out && <button className="ok-icon" title="Catat keluar" data-testid={`visit-checkout-${v.id}`} onClick={() => checkout(v)}><LogOut size={15}/></button>}<button className="danger-icon" title="Hapus" data-testid={`visit-delete-${v.id}`} onClick={() => remove(v)}><Trash2 size={15}/></button></div></td>
        </tr>)}</ShowMore>
        {rows.length === 0 && <tr><td colSpan={8} style={{ textAlign: "center", padding: 30, color: "#94a3b8" }} data-testid="visit-empty">{term ? `Tidak ada pengunjung bernama "${q.trim()}"` : "Belum ada pengunjung pada tanggal ini"}</td></tr>}
      </tbody></table></div>
    </div>
    {guest && <Modal title="Catat tamu" close={() => setGuest(false)}><form className="modal-form" onSubmit={addGuest} data-testid="guest-form">
      <label>Nama tamu<input data-testid="guest-name-input" required value={guestForm.name} onChange={(e) => setGuestForm({ ...guestForm, name: e.target.value })}/></label>
      <label>Asal / instansi<input data-testid="guest-origin-input" placeholder="mis. Guru, Orang tua, Dinas Pendidikan" value={guestForm.origin} onChange={(e) => setGuestForm({ ...guestForm, origin: e.target.value })}/></label>
      <label>Keperluan<select data-testid="guest-purpose-input" value={guestForm.purpose} onChange={(e) => setGuestForm({ ...guestForm, purpose: e.target.value })}>{GUEST_PURPOSES.map((p) => <option key={p}>{p}</option>)}</select></label>
      {guestForm.purpose === OTHER && <label>Tulis keperluan<input data-testid="guest-purpose-other-input" maxLength={120} placeholder="mis. Rapat komite, Survei akreditasi" value={guestOther} onChange={(e) => setGuestOther(e.target.value)}/></label>}
      <button className="primary full" data-testid="save-guest-button"><UserPlus size={16}/> Catat masuk</button>
    </form></Modal>}
    {purposeEdit && <Modal title="Tulis keperluan" close={() => setPurposeEdit(null)}><form className="modal-form" data-testid="purpose-edit-form" onSubmit={async (e) => { e.preventDefault(); const t = purposeEdit.text.trim(); if (!t) return; await changePurpose(purposeEdit.visit, t); setPurposeEdit(null); }}>
      <p className="account-hint" style={{ marginTop: 0 }}>Keperluan kunjungan <b>{purposeEdit.visit.name}</b>. Teks ini tampil di daftar pengunjung dan laporan.</p>
      <label>Keperluan<input autoFocus data-testid="purpose-edit-input" required maxLength={120} placeholder="mis. Rapat OSIS" value={purposeEdit.text} onChange={(e) => setPurposeEdit({ ...purposeEdit, text: e.target.value })}/></label>
      <button className="primary full" data-testid="purpose-edit-save">Simpan keperluan</button>
    </form></Modal>}
    {cfgOpen && <Modal title="Jam otomatis keluar" close={() => setCfgOpen(false)}><form className="modal-form" onSubmit={saveCfg}>
      <p className="account-hint" style={{ marginTop: 0 }}>Pengunjung yang belum scan keluar akan otomatis tercatat keluar pada jam ini (WIB). Yang masuk setelah jam ini ditutup pada akhir hari.</p>
      <label>Jam pulang sekolah<input type="time" data-testid="visit-config-time-input" required value={cfgTime} onChange={(e) => setCfgTime(e.target.value)}/></label>
      <button className="primary full" data-testid="save-visit-config-button">Simpan</button>
    </form></Modal>}
  </div>;
}
