
## Phase: Kelola Antrean Offline (Status: COMPLETED)
- Data yang ditolak server saat sinkron disimpan permanen di IndexedDB (store "rejected", DB v2)
- Petugas bisa: Coba lagi / Hapus / Hapus semua data ditolak; Batalkan data yang masih menunggu (konfirmasi 2 klik)
- Sesi login disalin ke perangkat saat login (aplikasi bisa dibuka ulang saat offline), dihapus saat logout
- Diuji: testing agent iteration_3 (100%) + uji manual retry sukses, hapus semua, batalkan saat offline

## Phase: Keyboard Pengunjung, PWA HP, PR GitHub (Status: COMPLETED)
- Pengunjung: kolom scan inputMode "none" (keyboard HP tidak langsung muncul), tombol keyboard untuk ketik manual
- PWA: Chrome installability OK, offline start_url OK; iPhone status bar "default" (tidak tertutup notch)
- PR #19 dibuat: devilatifa-dl/perpus branch fitur/offline-kartu-antrean-keyboard-pwa (token di /root/.secrets/github_token, chmod 600)

