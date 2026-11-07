# jalankan-backend-publik.ps1 - Jalankan backend lokal + tunnel Cloudflare, lalu (opsional) perbarui BACKEND_URL di Vercel.
#
# Pakai:
#   .\jalankan-backend-publik.ps1
#   .\jalankan-backend-publik.ps1 -VercelToken "xxx"
#
# Tanpa -VercelToken, skrip hanya menampilkan URL tunnel (isi BACKEND_URL manual).
#
# PENTING: URL trycloudflare.com berubah setiap kali dijalankan. Kalau URL berubah,
# BACKEND_URL di Vercel harus diperbarui (pakai -VercelToken agar otomatis).

param(
  [string]$VercelToken = "",
  [string]$VercelProject = "perpus",
  [int]$BackendPort = 8000
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

if (-not (Test-Path $cloudflared)) {
  $g = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($g) { $cloudflared = $g.Source }
}
if (-not (Test-Path $cloudflared)) {
  Write-Host "cloudflared tidak ditemukan. Install dulu:" -ForegroundColor Red
  Write-Host "  winget install --id Cloudflare.cloudflared" -ForegroundColor DarkGray
  exit 1
}
if (-not (Test-Path $python)) {
  Write-Host "Python venv backend tidak ditemukan: $python" -ForegroundColor Red
  exit 1
}

# 1. Pastikan MongoDB jalan
$mongo = @(Get-NetTCPConnection -LocalPort 27017 -State Listen -ErrorAction SilentlyContinue)
if ($mongo.Count -eq 0) {
  Write-Host "MongoDB belum jalan. Coba start service..." -ForegroundColor Yellow
  try { Start-Service MongoDB -ErrorAction Stop; Start-Sleep 5 } catch {
    Write-Host "  Gagal start service MongoDB (butuh Administrator)." -ForegroundColor Red
    Write-Host "  Jalankan mongod manual, lalu ulangi skrip ini." -ForegroundColor DarkGray
    exit 1
  }
}
Write-Host "MongoDB: OK" -ForegroundColor Green

# 2. Pastikan backend jalan
$be = @(Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue)
if ($be.Count -eq 0) {
  Write-Host "Menjalankan backend di port $BackendPort ..." -ForegroundColor Cyan
  Start-Process -FilePath $python -ArgumentList "-m","uvicorn","server:app","--host","127.0.0.1","--port","$BackendPort" -WorkingDirectory $backend -WindowStyle Minimized
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    $be = @(Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue)
    if ($be.Count -gt 0) { break }
  }
}
if ($be.Count -eq 0) {
  Write-Host "Backend gagal start di port $BackendPort" -ForegroundColor Red
  exit 1
}
Write-Host "Backend: OK (port $BackendPort)" -ForegroundColor Green

# 3. Jalankan tunnel, tangkap URL-nya
Write-Host ""
Write-Host "Membuka tunnel Cloudflare..." -ForegroundColor Cyan
$logFile = Join-Path $env:TEMP "perpus-tunnel.log"
if (Test-Path $logFile) { Remove-Item $logFile -Force }

$proc = Start-Process -FilePath $cloudflared -ArgumentList "tunnel","--url","http://127.0.0.1:$BackendPort","--no-autoupdate" -RedirectStandardError $logFile -RedirectStandardOutput "$logFile.out" -PassThru -WindowStyle Hidden

$url = $null
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Seconds 2
  if (Test-Path $logFile) {
    $txt = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
    if ($txt -match "https://[a-z0-9-]+\.trycloudflare\.com") {
      $url = $Matches[0]
      break
    }
  }
}

if (-not $url) {
  Write-Host "Gagal mendapatkan URL tunnel. Cek log: $logFile" -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "URL publik backend:" -ForegroundColor Cyan
Write-Host "  $url" -ForegroundColor Green
Write-Host ""

# 4. Uji tunnel
Write-Host "Menguji tunnel..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 15; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "$url/api/" -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
    if ($r.Content -match "aktif") { $ok = $true; break }
  } catch { }
  Start-Sleep -Seconds 3
}
if ($ok) { Write-Host "  Tunnel OK - backend dapat diakses dari internet" -ForegroundColor Green }
else { Write-Host "  Tunnel belum merespons. Tunggu 30 detik lalu coba buka $url/api/ di browser." -ForegroundColor Yellow }

# 5. Perbarui BACKEND_URL di Vercel (opsional)
if (-not $VercelToken) {
  Write-Host ""
  Write-Host "Langkah manual (2 menit):" -ForegroundColor Cyan
  Write-Host "  1. https://vercel.com -> project $VercelProject -> Settings -> Environment Variables"
  Write-Host "  2. BACKEND_URL = $url"
  Write-Host "  3. Deployments -> ... -> Redeploy"
  Write-Host ""
  Write-Host "Atau jalankan ulang dengan -VercelToken agar otomatis." -ForegroundColor DarkGray
  Write-Host ""
  Write-Host "Tunnel berjalan di PID $($proc.Id). Tutup dengan: Stop-Process -Id $($proc.Id)" -ForegroundColor DarkGray
  exit 0
}

Write-Host ""
Write-Host "Memperbarui BACKEND_URL di Vercel..." -ForegroundColor Cyan
$h = @{ Authorization = "Bearer $VercelToken"; "Content-Type" = "application/json" }

try {
  $projects = Invoke-RestMethod -Uri "https://api.vercel.com/v9/projects?limit=100" -Headers $h -Method Get -ErrorAction Stop
} catch {
  Write-Host "  Gagal baca project Vercel: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
$proj = $projects.projects | Where-Object { $_.name -eq $VercelProject } | Select-Object -First 1
if (-not $proj) {
  Write-Host "  Project '$VercelProject' tidak ditemukan. Yang ada:" -ForegroundColor Red
  $projects.projects | ForEach-Object { Write-Host "    - $($_.name)" }
  exit 1
}

# hapus env lama
try {
  $existing = Invoke-RestMethod -Uri "https://api.vercel.com/v9/projects/$($proj.id)/env" -Headers $h -Method Get -ErrorAction Stop
  foreach ($e in ($existing.envs | Where-Object { $_.key -eq "BACKEND_URL" })) {
    Invoke-RestMethod -Uri "https://api.vercel.com/v9/projects/$($proj.id)/env/$($e.id)" -Headers $h -Method Delete -ErrorAction SilentlyContinue | Out-Null
  }
} catch { }

$payload = @{ key = "BACKEND_URL"; value = $url; type = "plain"; target = @("production","preview","development") } | ConvertTo-Json -Depth 5
try {
  Invoke-RestMethod -Uri "https://api.vercel.com/v10/projects/$($proj.id)/env" -Headers $h -Method Post -Body $payload -ErrorAction Stop | Out-Null
  Write-Host "  BACKEND_URL = $url" -ForegroundColor Green
} catch {
  Write-Host "  Gagal set env: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

# redeploy
try {
  $deps = Invoke-RestMethod -Uri "https://api.vercel.com/v6/deployments?projectId=$($proj.id)&target=production&limit=1" -Headers $h -Method Get -ErrorAction Stop
  $last = $deps.deployments | Select-Object -First 1
  if ($last) {
    $body = @{ name = $proj.name; deploymentId = $last.uid; target = "production" } | ConvertTo-Json
    $new = Invoke-RestMethod -Uri "https://api.vercel.com/v13/deployments" -Headers $h -Method Post -Body $body -ErrorAction Stop
    Write-Host "  Redeploy: $($new.id)" -ForegroundColor Green
  }
} catch {
  Write-Host "  Redeploy otomatis gagal. Lakukan manual di dashboard." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Selesai. Uji: https://$VercelProject.vercel.app/api" -ForegroundColor Cyan
Write-Host "Tunnel PID $($proc.Id). Tutup dengan: Stop-Process -Id $($proc.Id)" -ForegroundColor DarkGray
