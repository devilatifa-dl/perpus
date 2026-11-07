# setup-render.ps1 - Buat backend Render (gratis) lewat Render API, lalu set env dan deploy.
#
# Pakai:
#   .\setup-render.ps1 -ApiKey "rnd_xxxx" -MongoUrl "mongodb+srv://..."
#
# Ambil API key di: https://dashboard.render.com/u/settings#api-keys
# (Account Settings -> API Keys -> Create API Key)
#
# Prasyarat: repo GitHub sudah terhubung ke akun Render
# (Dashboard -> New + -> Web Service -> connect GitHub sekali saja).
#
# Skrip ini idempoten: kalau service dengan nama sama sudah ada, env-nya yang
# diperbarui dan deploy dipicu ulang, bukan membuat service baru.

param(
  [Parameter(Mandatory = $true)][string]$ApiKey,
  [Parameter(Mandatory = $true)][string]$MongoUrl,
  [string]$NamaService = "perpus-backend",
  [string]$Repo = "https://github.com/devilatifa-dl/perpus",
  [string]$Branch = "main",
  [string]$FrontendUrl = "https://perpusmansa.vercel.app",
  [string]$Region = "singapore"
)

$ErrorActionPreference = "Stop"
$api = "https://api.render.com/v1"
$h = @{ Authorization = "Bearer $ApiKey"; Accept = "application/json"; "Content-Type" = "application/json" }

function Panggil($method, $path, $body) {
  $p = @{ Uri = "$api$path"; Headers = $h; Method = $method; TimeoutSec = 120 }
  if ($body) { $p.Body = ($body | ConvertTo-Json -Depth 10 -Compress) }
  return Invoke-RestMethod @p
}

Write-Host "=== 1. Cek API key ===" -ForegroundColor Cyan
try {
  $owners = Panggil "GET" "/owners?limit=20" $null
} catch {
  Write-Host "  API key ditolak: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
$owner = $owners[0].owner
if (-not $owner) { Write-Host "  Tidak ada owner." -ForegroundColor Red; exit 1 }
Write-Host "  Akun: $($owner.name) ($($owner.email))" -ForegroundColor Green
Write-Host "  ownerId: $($owner.id)"

Write-Host ""
Write-Host "=== 2. Cek service yang sudah ada ===" -ForegroundColor Cyan
$svc = $null
try {
  $daftar = Panggil "GET" "/services?limit=100" $null
  foreach ($item in $daftar) {
    if ($item.service.name -eq $NamaService) { $svc = $item.service; break }
  }
} catch { }

if ($svc) {
  Write-Host "  Sudah ada: $($svc.name) ($($svc.id)) - $($svc.suspended)" -ForegroundColor Yellow
} else {
  Write-Host "  Belum ada, membuat baru..." -ForegroundColor Cyan
  $body = @{
    type       = "web_service"
    name       = $NamaService
    ownerId    = $owner.id
    repo       = $Repo
    branch     = $Branch
    rootDir    = "backend"
    autoDeploy = "yes"
    envVars    = @(
      @{ key = "MONGO_URL"; value = $MongoUrl }
      @{ key = "DB_NAME"; value = "perpus" }
      @{ key = "FRONTEND_URL"; value = $FrontendUrl }
      @{ key = "PYTHON_VERSION"; value = "3.13.17" }
    )
    serviceDetails = @{
      env             = "python"
      plan            = "free"
      region          = $Region
      healthCheckPath = "/api/"
      envSpecificDetails = @{
        buildCommand = "pip install -r requirements.prod.txt"
        startCommand = "uvicorn server:app --host 0.0.0.0 --port `$PORT"
      }
    }
  }
  try {
    $svc = (Panggil "POST" "/services" $body).service
    Write-Host "  Dibuat: $($svc.id)" -ForegroundColor Green
  } catch {
    Write-Host "  GAGAL membuat service: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Kemungkinan repo belum terhubung ke Render." -ForegroundColor Yellow
    Write-Host "  Buka Dashboard -> New + -> Web Service -> hubungkan GitHub sekali," -ForegroundColor Yellow
    Write-Host "  lalu jalankan skrip ini lagi." -ForegroundColor Yellow
    exit 1
  }
}

Write-Host ""
Write-Host "=== 3. Set environment variables ===" -ForegroundColor Cyan
$envBody = @(
  @{ key = "MONGO_URL"; value = $MongoUrl }
  @{ key = "DB_NAME"; value = "perpus" }
  @{ key = "FRONTEND_URL"; value = $FrontendUrl }
  @{ key = "PYTHON_VERSION"; value = "3.13.17" }
)
try {
  Panggil "PUT" "/services/$($svc.id)/env-vars" $envBody | Out-Null
  Write-Host "  MONGO_URL, DB_NAME, FRONTEND_URL, PYTHON_VERSION -> OK" -ForegroundColor Green
} catch {
  Write-Host "  Gagal set env: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 4. Picu deploy ===" -ForegroundColor Cyan
try {
  $dep = Panggil "POST" "/services/$($svc.id)/deploys" @{ clearCache = "do_not_clear" }
  Write-Host "  Deploy: $($dep.id)" -ForegroundColor Green
} catch {
  Write-Host "  Gagal deploy: $($_.Exception.Message)" -ForegroundColor Red
}

$url = "https://$NamaService.onrender.com"
Write-Host ""
Write-Host "=== 5. Tunggu Live (maks 10 menit) ===" -ForegroundColor Cyan
Write-Host "  URL: $url"
$live = $false
for ($i = 1; $i -le 60; $i++) {
  Start-Sleep -Seconds 10
  try {
    $r = Invoke-WebRequest -Uri "$url/api/" -TimeoutSec 20 -UseBasicParsing -ErrorAction Stop
    if ($r.Content -match "aktif") {
      Write-Host "  LIVE setelah $($i * 10) detik" -ForegroundColor Green
      $live = $true
      break
    }
  } catch { }
  if ($i % 6 -eq 0) { Write-Host "  ... masih build ($($i * 10) detik)" -ForegroundColor DarkGray }
}

if (-not $live) {
  Write-Host "  Belum Live. Cek log di dashboard Render (tab Logs)." -ForegroundColor Yellow
  Write-Host "  Setelah Live, jalankan:" -ForegroundColor Yellow
  Write-Host "    .\scripts\cek-render.ps1 -Url $url -VercelToken <token>" -ForegroundColor DarkGray
  exit 1
}

Write-Host ""
Write-Host "=== 6. Arahkan Vercel ke Render ===" -ForegroundColor Cyan
Write-Host "  BACKEND_URL = $url"
Write-Host ""
Write-Host "  Otomatis (butuh token Vercel):" -ForegroundColor DarkGray
Write-Host "    .\scripts\cek-render.ps1 -Url $url -VercelToken <token>" -ForegroundColor DarkGray
Write-Host ""
Write-Host "SELESAI. Backend Render Live di $url" -ForegroundColor Green
