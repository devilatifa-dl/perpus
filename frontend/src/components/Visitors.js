import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Camera, CameraOff, CheckCircle2, Clock, DoorClosed, DoorOpen, LogIn, LogOut, ShieldAlert, UserCheck, Users, X } from "lucide-react";
import { api } from "../lib";
import { Modal } from "./Shared";
import { CameraScanner } from "./CameraScanner";
import { beep, cameraError, createCamera, unlockAudio } from "../lib/camera";

const COOLDOWN_MS = 1000;
const todayStr = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);
export const fmtClock = (d) => d ? new Date(d).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }) : "-";
export const fmtDur = (m) => m == null ? "-" : m > 60 ? `${Math.floor(m / 60)}j ${m % 60}m` : `${m}m`;
export const OUT_LABEL = { scan: "Scan keluar", manual: "Dicatat petugas" };

const OVERLAY = {
  masuk: { tone: "ok", label: "BERHASIL MASUK", icon: CheckCircle2 },
  keluar: { tone: "ok", label: "BERHASIL KELUAR", icon: CheckCircle2 },
  sudah_masuk: { tone: "warn", label: "SUDAH TERCATAT MASUK", icon: Clock },
  sudah_keluar: { tone: "warn", label: "SUDAH TERCATAT KELUAR", icon: Clock },
  error: { tone: "bad", label: "GAGAL", icon: AlertTriangle },
};

function LiveScanner({ onCode }) {
  return (
    <div className="visit-cam" data-testid="visit-camera">
      <CameraScanner onCode={onCode} testId="visit-camera-scanner" />
    </div>
  );
}

export function Visitors() {
  const [tab, setTab] = useState("live");
  const [hit, setHit] = useState(null);
  const [logs, setLogs] = useState([]);
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("masuk");
  const cb = useRef(null);
  const timer = useRef(null);
  const lock = useRef(false);

  const handleScan = async (text) => {
    if (lock.current) return;
    lock.current = true;
    try {
      unlockAudio();
      const res = await api.post("/visitors/scan", { code: text, mode });
      setHit({ ...res, action: res.status });
      beep(res.status === "masuk" || res.status === "keluar" ? "ok" : "warn");
      loadLogs();
    } catch (e) {
      setHit({ action: "error", message: e.message || "Gagal memproses" });
      beep("error");
    } finally {
      setTimeout(() => {
        lock.current = false;
      }, COOLDOWN_MS);
    }
  };

  const loadLogs = async () => {
    try {
      const res = await api.get(`/visitors/logs?date=${todayStr()}`);
      setLogs(res);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <div className="visitors-page" data-testid="visitors-page">
      <div className="visitors-header">
        <h2>Buku Tamu & Kunjungan</h2>
        <div className="tabs">
          <button className={`btn ${tab === "live" ? "btn-primary" : "btn-secondary"}`} onClick={() => setTab("live")}>Scan Live</button>
          <button className={`btn ${tab === "logs" ? "btn-primary" : "btn-secondary"}`} onClick={() => setTab("logs")}>Riwayat Hari Ini</button>
        </div>
      </div>

      {tab === "live" && (
        <div className="live-grid">
          <div className="scanner-card">
            <div className="mode-toggle">
              <button className={`btn ${mode === "masuk" ? "btn-success" : "btn-outline"}`} onClick={() => setMode("masuk")}>Masuk</button>
              <button className={`btn ${mode === "keluar" ? "btn-warning" : "btn-outline"}`} onClick={() => setMode("keluar")}>Keluar</button>
            </div>
            <LiveScanner onCode={handleScan} />
          </div>
          <div className="result-card">
            {hit ? (
              <div className={`hit-box ${OVERLAY[hit.action]?.tone || "bad"}`}>
                <h3>{OVERLAY[hit.action]?.label || hit.message}</h3>
                <p>{hit.name || hit.code}</p>
              </div>
            ) : (
              <div className="hit-box empty">Arahkan kartu ke kamera</div>
            )}
          </div>
        </div>
      )}

      {tab === "logs" && (
        <div className="logs-card">
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Waktu</th>
                  <th>Nama</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l, i) => (
                  <tr key={i}>
                    <td>{fmtClock(l.time)}</td>
                    <td>{l.name}</td>
                    <td>{l.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
