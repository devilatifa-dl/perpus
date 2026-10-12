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

export const readFile = (file) => new Promise((resolve, reject) => {
  if (!file) return resolve("");
  if (file.size > 900 * 1024) return reject(new Error("Ukuran maksimal 900KB"));
  const r = new FileReader(); r.onload = () => resolve(r.result); r.onerror = reject; r.readAsDataURL(file);
});
