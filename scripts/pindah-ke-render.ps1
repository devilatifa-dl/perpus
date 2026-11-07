# pindah-ke-render.ps1 - Satu perintah: migrasi data ke Atlas + buat backend Render + arahkan Vercel.
#
# Pakai:
#   .\pindah-ke-render.ps1 `
#       -MongoUrl "mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net" `
#       -RenderApiKey "rnd_xxxx" `
#       -VercelToken "xxxx"
#
# Yang dilakukan, berurutan:
#   1. Uji koneksi Atlas
#   2. Salin semua data lokal -> Atlas (termasuk foto anggota dan cover buku)
#   3. Buat / perbarui service backend di Render (paket free)
#   4. Tunggu sampai Render Live
#   5. Set BACKEND_URL di Vercel + redeploy
#   6. Uji hasil akhir
#
# Semua gratis. Tidak ada langganan, tidak ada kartu kredit.
#
# Kalau satu langkah gagal, skrip berhenti dan memberi tahu langkah mana yang
# perlu dibereskan. Data lokal TIDAK diubah sama sekali.

param(
  [Parameter(Mandatory = $true)][string]$MongoUrl,
  [Parameter(Mandatory = $true)][string]$RenderApiKey,
  [Parameter(Mandatory = $true)][string]$VercelToken,
  [string]$NamaService = "perpus-backend",
  [string]$VercelProject = "perpus",
  [string]$FrontendUrl = "https://perpusmansa.vercel.app",
  [switch]$LewatiMigrasi
)

$ErrorActionPreference = "Continue"
$akar = Split-Path -Parent $PSScriptRoot
$python = Join-Path $akar "backend\.venv\Scripts\python.exe"
$gagal = 0

function Judul($teks) {
  Write-Host ""
  Write-Host ("=" * 62) -ForegroundColor DarkCyan
  Write-Host "  $teks" -ForegroundColor Cyan
  Write-Host ("=" * 62) -ForegroundColor DarkCyan
}

# ---------------------------------------------------------------- 1. Atlas
Judul "1/6  Uji koneksi MongoDB Atlas"

if (-not (Test-Path $python)) {
  Write-Host "  Python venv backend tidak ditemukan: $python" -ForegroundColor Red
  exit 1
}

$uji = @'
import sys, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
async def m():
    c = AsyncIOMotorClient(sys.argv[1], serverSelectionTimeoutMS=20000)
    try:
        await c.admin.command("ping")
        print("OK")
    except Exception as e:
        print("GAGAL: " + str(e))
        sys.exit(1)
    finally:
        c.close()
asyncio.run(m())
'@
$ujiPath = Join-Path $env:TEMP "uji-atlas.py"
[System.IO.File]::WriteAllText($ujiPath, $uji, (New-Object System.Text.UTF8Encoding($false)))
$hasil = & $python $ujiPath $MongoUrl 2>&1
Remove-Item $ujiPath -Force -ErrorAction SilentlyContinue

if ($hasil -notmatch "OK") {
  Write-Host "  $hasil" -ForegroundColor Red
  Write-Host ""
  Write-Host "  Periksa:" -ForegroundColor Yellow
  Write-Host "   - Password benar (karakter khusus harus di-encode, mis. @ -> %40)"
  Write-Host "   - Network Access Atlas sudah berisi 0.0.0.0/0"
  Write-Host "   - Nama cluster benar"
  exit 1
}
Write-Host "  Atlas dapat dihubungi" -ForegroundColor Green

# ------------------------------------------------------------- 2. Migrasi
Judul "2/6  Salin data lokal ke Atlas"

if ($LewatiMigrasi) {
  Write-Host "  Dilewati (-LewatiMigrasi)" -ForegroundColor Yellow
} else {
  $migrasi = Join-Path $akar "scripts\migrasi-ke-atlas.py"
  & $python $migrasi $MongoUrl
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  Migrasi gagal. Perbaiki dulu, lalu jalankan ulang." -ForegroundColor Red
    exit 1
  }
}

# -------------------------------------------------------------- 3. Render
Judul "3/6  Buat backend di Render (paket free)"

$setup = Join-Path $akar "scripts\setup-render.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $setup `
  -ApiKey $RenderApiKey -MongoUrl $MongoUrl -NamaService $NamaService `
  -FrontendUrl $FrontendUrl
if ($LASTEXITCODE -ne 0) {
  Write-Host "  Setup Render gagal. Lihat pesan di atas." -ForegroundColor Red
  exit 1
}

$renderUrl = "https://$NamaService.onrender.com"

# -------------------------------------------------------------- 4. Vercel
Judul "4/6  Arahkan Vercel ke Render"

$cek = Join-Path $akar "scripts\cek-render.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $cek `
  -Url $renderUrl -VercelToken $VercelToken -VercelProject $VercelProject
if ($LASTEXITCODE -ne 0) {
  Write-Host "  Gagal mengarahkan Vercel." -ForegroundColor Red
  $gagal = 1
}

# ---------------------------------------------------------------- 5. Uji
Judul "5/6  Uji hasil akhir"

Write-Host "  Menunggu Vercel selesai redeploy (90 detik)..." -ForegroundColor DarkGray
Start-Sleep -Seconds 90

$domain = "https://$VercelProject.vercel.app"
$apiOk = $false
for ($i = 1; $i -le 12; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "$domain/api/" -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
    if ($r.Content -match "aktif") { $apiOk = $true; break }
  } catch { }
  Start-Sleep -Seconds 10
}

if ($apiOk) {
  Write-Host "  $domain/api/ -> 200 OK" -ForegroundColor Green
} else {
  Write-Host "  $domain/api/ belum merespons. Cek dashboard Vercel." -ForegroundColor Yellow
  $gagal = 1
}

# Login + hitung data
try {
  $body = @{ email = "admin@smansa.sch.id"; password = "admin123" } | ConvertTo-Json
  $tok = (Invoke-RestMethod "$domain/api/auth/login" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60).token
  $h = @{ Authorization = "Bearer " + $tok }
  $m = Invoke-RestMethod "$domain/api/members" -Headers $h -TimeoutSec 90
  $b = Invoke-RestMethod "$domain/api/books" -Headers $h -TimeoutSec 90
  $guru = @($m | Where-Object { $_.member_type -eq "guru" }).Count
  Write-Host "  Login OK" -ForegroundColor Green
  Write-Host "  Anggota: $($m.Count) (guru: $guru)" -ForegroundColor Green
  Write-Host "  Buku   : $($b.Count)" -ForegroundColor Green

  $lbS = Invoke-RestMethod "$domain/api/visits/leaderboard?audience=siswa" -Headers $h -TimeoutSec 90
  $lbG = Invoke-RestMethod "$domain/api/visits/leaderboard?audience=guru" -Headers $h -TimeoutSec 90
  Write-Host "  Peringkat siswa: $($lbS.total_visits) kunjungan" -ForegroundColor Green
  Write-Host "  Peringkat guru : $($lbG.total_visits) kunjungan" -ForegroundColor Green

  if ($m.Count -eq 0 -or $b.Count -eq 0) {
    Write-Host "  Data kosong di backend baru. Ulangi migrasi." -ForegroundColor Red
    $gagal = 1
  }
} catch {
  Write-Host "  Uji login/data gagal: $($_.Exception.Message)" -ForegroundColor Yellow
  $gagal = 1
}

# ------------------------------------------------------------ 6. Ringkasan
Judul "6/6  Ringkasan"

Write-Host "  Backend Render : $renderUrl"
Write-Host "  Frontend       : $domain"
Write-Host "  Database       : MongoDB Atlas (M0 free, 512 MB)"
Write-Host ""

if ($gagal -eq 0) {
  Write-Host "  SELESAI. Situs sudah memakai Render + Atlas, 100% gratis." -ForegroundColor Green
  Write-Host ""
  Write-Host "  Langkah terakhir agar backend tidak tidur:" -ForegroundColor Cyan
  Write-Host "    Daftar https://cron-job.org (gratis)"
  Write-Host "    Buat cron: URL $renderUrl/api/  setiap 10 menit"
  Write-Host ""
  Write-Host "  Setelah yakin stabil, tunnel Cloudflare di laptop boleh dimatikan." -ForegroundColor DarkGray
  exit 0
} else {
  Write-Host "  Ada langkah yang belum beres. Lihat pesan kuning/merah di atas." -ForegroundColor Yellow
  Write-Host "  Panduan lengkap: PANDUAN_PINDAH_RENDER.md" -ForegroundColor DarkGray
  exit 1
}
