import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true });
export const fmt = (value) => new Intl.NumberFormat("id-ID").format(value || 0);
export const fmtDate = (d, opts = { day: "numeric", month: "short", year: "numeric" }) => d ? new Date(d).toLocaleDateString("id-ID", opts) : "-";

export const SCHOOL_LOGO = "/logo-sekolah.png";
export const LIBRARY_LOGO = "/logo-perpustakaan.png";
export const DEFAULT_SETTINGS = { school_logo: "", library_logo: "", card_theme: "navy", card_layout: "classic", card_show_qr: true, card_show_address: true, card_title: "KARTU ANGGOTA PERPUSTAKAAN", card_font: "modern", card_school_spacing: 0, card_logo_pos: "kiri", card_photo_pos: "kiri", card_qr_pos: "atas" };
export const CARD_THEMES = [["navy", "Biru Navy"], ["emerald", "Hijau Zamrud"], ["maroon", "Merah Maroon"], ["sunset", "Jingga Senja"], ["midnight", "Hitam Emas"], ["light", "Putih Bersih"], ["book", "Tema Buku"]];
export const CARD_LAYOUTS = [["classic", "Klasik", "Foto kiri, QR di atas"], ["modern", "Modern", "QR kiri, foto kanan"], ["portrait", "Potret", "Vertikal, QR di bawah"]];
export const CARD_FONTS = [["modern", "Modern"], ["klasik", "Klasik"], ["elegan", "Elegan"], ["mono", "Monospace"]];
export const CARD_POS = { logo: [["kiri", "Kiri"], ["tengah", "Tengah"], ["kanan", "Kanan"]], photo: [["kiri", "Kiri"], ["kanan", "Kanan"]], qr: [["atas", "Atas"], ["bawah", "Bawah"]] };
export const CARD_PRESETS = [
  ["klasik-navy", "Klasik Navy", { card_theme: "navy", card_layout: "classic", card_font: "modern", card_logo_pos: "kiri", card_photo_pos: "kiri", card_qr_pos: "atas", card_school_spacing: 0 }],
  ["buku-elegan", "Buku Elegan", { card_theme: "book", card_layout: "classic", card_font: "elegan", card_logo_pos: "tengah", card_photo_pos: "kiri", card_qr_pos: "atas", card_school_spacing: 1.5 }],
  ["modern-zamrud", "Modern Zamrud", { card_theme: "emerald", card_layout: "modern", card_font: "modern", card_logo_pos: "kiri", card_photo_pos: "kanan", card_qr_pos: "bawah", card_school_spacing: 0.5 }],
  ["potret-maroon", "Potret Maroon", { card_theme: "maroon", card_layout: "portrait", card_font: "klasik", card_logo_pos: "tengah", card_photo_pos: "kiri", card_qr_pos: "bawah", card_school_spacing: 1 }],
  ["hitam-emas", "Hitam Emas", { card_theme: "midnight", card_layout: "classic", card_font: "elegan", card_logo_pos: "kanan", card_photo_pos: "kanan", card_qr_pos: "atas", card_school_spacing: 2 }],
  ["putih-minimal", "Putih Minimalis", { card_theme: "light", card_layout: "modern", card_font: "mono", card_logo_pos: "kiri", card_photo_pos: "kiri", card_qr_pos: "bawah", card_school_spacing: 0 }],
];

export const readFile = (file) => new Promise((resolve, reject) => {
  if (!file) return resolve("");
  if (file.size > 900 * 1024) return reject(new Error("Ukuran maksimal 900KB"));
  const r = new FileReader(); r.onload = () => resolve(r.result); r.onerror = reject; r.readAsDataURL(file);
});
