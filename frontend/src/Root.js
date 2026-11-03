import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import PortalChooser from "@/components/PortalChooser";
import PwaStatus from "@/components/PwaStatus";

// Halaman admin & siswa dimuat terpisah: HP hanya mengunduh kode halaman yang dibuka.
const loadStaff = () => import("./App");
const loadStudent = () => import("@/components/StudentPortal");
const StaffApp = lazy(() => loadStaff().then((m) => ({ default: m.StaffApp })));
const StudentPortal = lazy(loadStudent);

function Loading() {
  return <div className="loading" data-testid="page-loading"><div className="boot-loader"><img src="/icons/icon-192.png" alt="" width="64" height="64"/><span>Memuat...</span></div></div>;
}

// Setelah halaman pemilih tampil, unduh kode halaman lain di waktu senggang (perpindahan terasa instan)
function IdlePrefetch() {
  const { pathname } = useLocation();
  useEffect(() => {
    if (pathname !== "/") return undefined;
    const conn = navigator.connection;
    if (conn && (conn.saveData || /2g/.test(conn.effectiveType || ""))) return undefined;
    const run = () => { loadStudent().catch(() => {}); loadStaff().catch(() => {}); };
    const id = window.requestIdleCallback ? window.requestIdleCallback(run, { timeout: 4000 }) : setTimeout(run, 2500);
    return () => (window.cancelIdleCallback ? window.cancelIdleCallback(id) : clearTimeout(id));
  }, [pathname]);
  return null;
}

export default function Root() {
  return <BrowserRouter>
    <Suspense fallback={<Loading/>}>
      <Routes>
        <Route path="/" element={<PortalChooser/>}/>
        <Route path="/admin/*" element={<StaffApp/>}/>
        <Route path="/siswa/*" element={<StudentPortal/>}/>
        <Route path="*" element={<Navigate to="/" replace/>}/>
      </Routes>
    </Suspense>
    <IdlePrefetch/>
    <PwaStatus/>
  </BrowserRouter>;
}
