# cek-render.ps1 - Cek apakah backend Render sudah Live, lalu (opsional) isi BACKEND_URL di Vercel otomatis.
#
# Pakai:
#   .\cek-render.ps1                                  # cek kandidat URL saja
#   .\cek-render.ps1 -Url https://xxx.onrender.com    # cek satu URL tertentu
#   .\cek-render.ps1 -Url https://xxx.onrender.com -VercelToken "xxx"   # cek + isi env Vercel otomatis
#
# Tanpa -VercelToken, skrip hanya melapor. Tidak mengubah apa pun.

param(
  [string]$Url = "",
  [string]$VercelToken = "",
  [string]$VercelProject = "perpus",
  [int]$TimeoutSec = 90
)

$ErrorActionPreference = "Continue"

function Test-Backend {
  param([string]$Base)
  $target = ($Base.TrimEnd("/")) + "/api"
  try {
    $r = Invoke-WebRequest -Uri $target -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
    $body = $r.Content
    if ($r.StatusCode -eq 200 -and $body -match "aktif") {
      return @{ ok = $true; status = $r.StatusCode; body = $body.Trim() }
    }
    return @{ ok = $false; status = $r.StatusCode; body = $body.Substring(0, [Math]::Min(120, $body.Length)) }
  } catch {
    $code = "-"
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    return @{ ok = $false; status = $code; body = $_.Exception.Message }
  }
}

Write-Host ""
Write-Host "=== Cek backend Render ===" -ForegroundColor Cyan

$candidates = @()
if ($Url) {
  $candidates = @($Url)
} else {
  # Kandidat nama umum. Render menambah akhiran acak bila nama sudah dipakai.
  $candidates = @(
    "https://perpus-backend.onrender.com",
    "https://perpus-backend-1.onrender.com",
    "https://perpus-backend-abc1.onrender.com",
    "https://perpus.onrender.com",
    "https://perpus-api.onrender.com"
  )
  Write-Host "Tidak ada -Url. Menguji $($candidates.Count) kandidat nama umum." -ForegroundColor DarkGray
  Write-Host "Kalau nama layanan Anda berbeda, jalankan ulang dengan -Url." -ForegroundColor DarkGray
}

$live = $null
foreach ($c in $candidates) {
  Write-Host -NoNewline ("  {0,-45} " -f $c)
  $res = Test-Backend -Base $c
  if ($res.ok) {
    Write-Host "LIVE  ($($res.body))" -ForegroundColor Green
    if (-not $live) { $live = $c }
  } else {
    Write-Host "belum  (HTTP $($res.status))" -ForegroundColor DarkYellow
  }
}

Write-Host ""
if (-not $live) {
  Write-Host "Belum ada backend Render yang Live." -ForegroundColor Yellow
  Write-Host ""
  Write-Host "Cara membuatnya (sekali saja, gratis):" -ForegroundColor Cyan
  Write-Host "  1. https://render.com -> daftar pakai GitHub"
  Write-Host "  2. New + -> Blueprint -> pilih repo devilatifa-dl/perpus -> Apply"
  Write-Host "  3. Isi MONGO_URL (dari MongoDB Atlas) dan FRONTEND_URL"
  Write-Host "  4. Tunggu status Live (sekitar 5 menit)"
  Write-Host "  5. Jalankan ulang skrip ini dengan -Url https://<nama-layanan>.onrender.com"
  Write-Host ""
  Write-Host "Panduan lengkap: PANDUAN_PINDAH_RENDER.md" -ForegroundColor DarkGray
  exit 1
}

Write-Host "Backend Live: $live" -ForegroundColor Green

if (-not $VercelToken) {
  Write-Host ""
  Write-Host "Langkah berikutnya (manual, 2 menit):" -ForegroundColor Cyan
  Write-Host "  1. https://vercel.com -> project $VercelProject -> Settings -> Environment Variables"
  Write-Host "  2. Add New:  BACKEND_URL = $live"
  Write-Host "  3. Deployments -> deployment terakhir -> ... -> Redeploy"
  Write-Host ""
  Write-Host "Atau jalankan ulang dengan -VercelToken agar terisi otomatis:" -ForegroundColor DarkGray
  Write-Host "  .\cek-render.ps1 -Url $live -VercelToken `"<token-vercel>`"" -ForegroundColor DarkGray
  exit 0
}

# === Isi BACKEND_URL di Vercel otomatis ===
Write-Host ""
Write-Host "=== Isi BACKEND_URL di Vercel ===" -ForegroundColor Cyan

$headers = @{
  Authorization  = "Bearer $VercelToken"
  "Content-Type" = "application/json"
}

# 1. Cari project id
try {
  $projects = Invoke-RestMethod -Uri "https://api.vercel.com/v9/projects?limit=100" -Headers $headers -Method Get -ErrorAction Stop
} catch {
  Write-Host "Gagal membaca daftar project Vercel: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "Pastikan token punya izin project. Buat di https://vercel.com/account/tokens" -ForegroundColor DarkGray
  exit 1
}

$proj = $projects.projects | Where-Object { $_.name -eq $VercelProject } | Select-Object -First 1
if (-not $proj) {
  Write-Host "Project '$VercelProject' tidak ditemukan. Project yang ada:" -ForegroundColor Red
  $projects.projects | ForEach-Object { Write-Host "  - $($_.name)" }
  exit 1
}
Write-Host "  project: $($proj.name) ($($proj.id))"

# 2. Hapus env BACKEND_URL lama (semua target), lalu buat baru
try {
  $existing = Invoke-RestMethod -Uri "https://api.vercel.com/v9/projects/$($proj.id)/env" -Headers $headers -Method Get -ErrorAction Stop
  foreach ($e in ($existing.envs | Where-Object { $_.key -eq "BACKEND_URL" })) {
    Invoke-RestMethod -Uri "https://api.vercel.com/v9/projects/$($proj.id)/env/$($e.id)" -Headers $headers -Method Delete -ErrorAction SilentlyContinue | Out-Null
    Write-Host "  hapus env lama: $($e.id)"
  }
} catch {
  Write-Host "  (tidak ada env lama / gagal baca: $($_.Exception.Message))" -ForegroundColor DarkGray
}

$payload = @{
  key    = "BACKEND_URL"
  value  = $live
  type   = "plain"
  target = @("production", "preview", "development")
} | ConvertTo-Json -Depth 5

try {
  $created = Invoke-RestMethod -Uri "https://api.vercel.com/v10/projects/$($proj.id)/env" -Headers $headers -Method Post -Body $payload -ErrorAction Stop
  Write-Host "  BACKEND_URL = $live  (dibuat)" -ForegroundColor Green
} catch {
  Write-Host "  Gagal membuat env: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

# 3. Redeploy production terakhir
Write-Host ""
Write-Host "=== Redeploy ===" -ForegroundColor Cyan
try {
  $deps = Invoke-RestMethod -Uri "https://api.vercel.com/v6/deployments?projectId=$($proj.id)&target=production&limit=1" -Headers $headers -Method Get -ErrorAction Stop
  $last = $deps.deployments | Select-Object -First 1
  if ($last) {
    $body = @{ name = $proj.name; deploymentId = $last.uid; target = "production" } | ConvertTo-Json
    $new = Invoke-RestMethod -Uri "https://api.vercel.com/v13/deployments" -Headers $headers -Method Post -Body $body -ErrorAction Stop
    Write-Host "  redeploy dibuat: $($new.id)" -ForegroundColor Green
    Write-Host "  tunggu sekitar 1-2 menit, lalu uji: https://$VercelProject.vercel.app/api"
  } else {
    Write-Host "  Tidak ada deployment production. Deploy manual dari dashboard." -ForegroundColor Yellow
  }
} catch {
  Write-Host "  Redeploy otomatis gagal: $($_.Exception.Message)" -ForegroundColor Yellow
  Write-Host "  Lakukan manual: Vercel -> Deployments -> ... -> Redeploy" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Selesai. Uji: https://$VercelProject.vercel.app/api" -ForegroundColor Cyan
