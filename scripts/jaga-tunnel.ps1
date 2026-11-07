# jaga-tunnel.ps1 - Jaga tunnel Cloudflare tetap hidup dan BACKEND_URL di Vercel selalu benar.
#
# Pakai:
#   .\jaga-tunnel.ps1 -VercelToken "xxx"
#
# Yang dilakukan berulang setiap 60 detik:
#   1. Cek apakah URL tunnel masih merespons /api/
#   2. Kalau mati: nyalakan cloudflared baru, ambil URL baru
#   3. Perbarui BACKEND_URL di Vercel + redeploy
#   4. Ulangi
#
# Ini hanya untuk masa transisi sebelum pindah ke Render. Untuk pemakaian
# harian, Render + Atlas lebih baik karena tidak butuh laptop menyala.
#
# Hentikan dengan Ctrl+C.

param(
  [Parameter(Mandatory = $true)][string]$VercelToken,
  [string]$VercelProject = "perpus",
  [int]$BackendPort = 8000,
  [int]$IntervalDetik = 60
)

$ErrorActionPreference = "Continue"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (-not (Test-Path $cloudflared)) {
  $g = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($g) { $cloudflared = $g.Source } else {
    Write-Host "cloudflared tidak ditemukan. Install: winget install --id Cloudflare.cloudflared" -ForegroundColor Red
    exit 1
  }
}

$logFile = Join-Path $env:TEMP "perpus-tunnel3.log"
$urlSekarang = ""
$projId = ""

function Tulis($teks, $warna = "Gray") {
  Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $teks) -ForegroundColor $warna
}

function AmbilProyekId {
  $h = @{ Authorization = "Bearer " + $VercelToken; "Content-Type" = "application/json" }
  try {
    $p = Invoke-RestMethod "https://api.vercel.com/v9/projects?limit=100" -Headers $h -TimeoutSec 60
    $proj = $p.projects | Where-Object { $_.name -eq $VercelProject } | Select-Object -First 1
    if ($proj) { return $proj.id }
  } catch { }
  return ""
}

function SetBackendUrl($url) {
  if (-not $projId) { Tulis "  proyek Vercel tidak ditemukan, BACKEND_URL tidak diubah" "Yellow"; return $false }
  $h = @{ Authorization = "Bearer " + $VercelToken; "Content-Type" = "application/json" }
  try {
    $envs = Invoke-RestMethod "https://api.vercel.com/v9/projects/$projId/env" -Headers $h -TimeoutSec 60
    foreach ($e in ($envs.envs | Where-Object { $_.key -eq "BACKEND_URL" })) {
      Invoke-RestMethod "https://api.vercel.com/v9/projects/$projId/env/$($e.id)" -Headers $h -Method Delete -TimeoutSec 60 | Out-Null
    }
    $body = @{ key = "BACKEND_URL"; value = $url; type = "plain"; target = @("production", "preview", "development") } | ConvertTo-Json -Depth 5
    Invoke-RestMethod "https://api.vercel.com/v10/projects/$projId/env" -Headers $h -Method Post -Body $body -TimeoutSec 60 | Out-Null
    Tulis "  BACKEND_URL = $url" "Green"

    $deps = Invoke-RestMethod "https://api.vercel.com/v6/deployments?projectId=$projId&target=production&limit=1" -Headers $h -TimeoutSec 60
    $last = $deps.deployments | Select-Object -First 1
    if ($last) {
      $b = @{ name = $VercelProject; deploymentId = $last.uid; target = "production" } | ConvertTo-Json
      $new = Invoke-RestMethod "https://api.vercel.com/v13/deployments" -Headers $h -Method Post -Body $b -TimeoutSec 60
      Tulis "  redeploy: $($new.id)" "Green"
    }
    return $true
  } catch {
    Tulis "  gagal set BACKEND_URL: $($_.Exception.Message)" "Red"
    return $false
  }
}

function TunnelHidup($url) {
  if (-not $url) { return $false }
  try {
    $r = Invoke-WebRequest "$url/api/" -TimeoutSec 20 -UseBasicParsing -ErrorAction Stop
    return ($r.Content -match "aktif")
  } catch { return $false }
}

function NyalakanTunnel {
  # Jangan matikan tunnel yang sedang dipakai produksi. Kalau ada proses
  # cloudflared hidup, pakai URL-nya kalau masih merespons.
  $hidup = @(Get-Process cloudflared -ErrorAction SilentlyContinue)
  if ($hidup.Count -gt 0) {
    if (Test-Path $logFile) {
      $t = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
      if ($t -match "https://[a-z0-9-]+\.trycloudflare\.com") {
        $lama = $Matches[0]
        if (TunnelHidup $lama) { return $lama }
      }
    }
    Tulis "  cloudflared hidup tapi URL tidak merespons - membiarkannya, tidak dimatikan" "Yellow"
    return ""
  }

  Remove-Item $logFile, "$logFile.out" -Force -ErrorAction SilentlyContinue
  Start-Process -FilePath $cloudflared -ArgumentList "tunnel", "--url", "http://127.0.0.1:$BackendPort", "--no-autoupdate" `
    -RedirectStandardError $logFile -RedirectStandardOutput "$logFile.out" -WindowStyle Hidden | Out-Null

  for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Path $logFile) {
      $t = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
      if ($t -match "https://[a-z0-9-]+\.trycloudflare\.com") { return $Matches[0] }
    }
  }
  return ""
}

# --- Mulai ---
Tulis "=== Jaga tunnel aktif ===" "Cyan"
$projId = AmbilProyekId
if ($projId) { Tulis "proyek Vercel: $VercelProject ($projId)" "Green" }
else { Tulis "proyek Vercel '$VercelProject' tidak ditemukan - hanya tunnel yang dijaga" "Yellow" }

$backend = @(Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue)
if ($backend.Count -eq 0) {
  Tulis "backend port $BackendPort belum jalan. Nyalakan dulu, lalu ulangi." "Red"
  exit 1
}
Tulis "backend port ${BackendPort}: OK" "Green"

# Ambil URL yang sedang dipakai Vercel kalau ada
if ($projId) {
  try {
    $h = @{ Authorization = "Bearer " + $VercelToken }
    $envs = Invoke-RestMethod "https://api.vercel.com/v9/projects/$projId/env" -Headers $h -TimeoutSec 60
    $cur = $envs.envs | Where-Object { $_.key -eq "BACKEND_URL" } | Select-Object -First 1
    if ($cur) { $urlSekarang = $cur.value }
  } catch { }
}

if (TunnelHidup $urlSekarang) {
  Tulis "tunnel sekarang hidup: $urlSekarang" "Green"
} else {
  Tulis "tunnel mati atau belum ada, menyalakan..." "Yellow"
  $urlSekarang = NyalakanTunnel
  if ($urlSekarang) {
    Tulis "URL baru: $urlSekarang" "Green"
    SetBackendUrl $urlSekarang | Out-Null
  } else {
    Tulis "gagal menyalakan tunnel" "Red"
  }
}

Tulis "memantau setiap $IntervalDetik detik. Ctrl+C untuk berhenti." "Cyan"
while ($true) {
  Start-Sleep -Seconds $IntervalDetik

  $backend = @(Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue)
  if ($backend.Count -eq 0) {
    Tulis "backend port ${BackendPort} mati - menunggu hidup kembali" "Red"
    continue
  }

  if (TunnelHidup $urlSekarang) { continue }

  Tulis "tunnel mati, menyalakan ulang..." "Yellow"
  $baru = NyalakanTunnel
  if ($baru) {
    $urlSekarang = $baru
    Tulis "URL baru: $urlSekarang" "Green"
    SetBackendUrl $urlSekarang | Out-Null
  } else {
    Tulis "gagal menyalakan tunnel, coba lagi 60 detik" "Red"
  }
}
