import { useEffect, useState } from "react";

// Mode tampilan: "light" | "dark". Pilihan manual disimpan; jika belum pernah
// memilih, mengikuti pengaturan HP/komputer (prefers-color-scheme).
const KEY = "perpus-theme";
const media = () => (typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null);

export const storedTheme = () => { try { const v = localStorage.getItem(KEY); return v === "dark" || v === "light" ? v : null; } catch { return null; } };
export const systemTheme = () => (media()?.matches ? "dark" : "light");

const listeners = new Set();
let current = typeof document !== "undefined" ? (document.documentElement.dataset.theme || storedTheme() || systemTheme()) : "light";

export function applyTheme(theme) {
  current = theme;
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", theme === "dark" ? "#120f22" : "#7c3aed");
  listeners.forEach((fn) => fn(theme));
}

export function setTheme(theme) {
  try { localStorage.setItem(KEY, theme); } catch { /* abaikan */ }
  const root = document.documentElement;
  root.classList.add("theme-anim");
  applyTheme(theme);
  clearTimeout(window.__perpusThemeT);
  window.__perpusThemeT = setTimeout(() => root.classList.remove("theme-anim"), 400);
}

if (typeof window !== "undefined") {
  applyTheme(current);
  const mq = media();
  const onSystem = (e) => { if (!storedTheme()) applyTheme(e.matches ? "dark" : "light"); };
  if (mq?.addEventListener) mq.addEventListener("change", onSystem); else if (mq?.addListener) mq.addListener(onSystem);
  window.addEventListener("storage", (e) => { if (e.key === KEY) applyTheme(storedTheme() || systemTheme()); });
}

export function useTheme() {
  const [theme, set] = useState(current);
  useEffect(() => { listeners.add(set); set(current); return () => listeners.delete(set); }, []);
  return [theme, () => setTheme(theme === "dark" ? "light" : "dark")];
}
