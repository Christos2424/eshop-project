# Serves the shop from this PC and gives it a temporary public HTTPS address.
# Installs cloudflared on the first run if it is missing (winget, or a direct download into venv\).
# Run from the flask_eshop folder:  powershell -ExecutionPolicy Bypass -File deploy\start_public.ps1
# Stop with Ctrl+C (the public address stops working when this window closes).

$env:SESSION_COOKIE_SECURE = '1'   # the tunnel serves HTTPS
$localCopy = Join-Path (Get-Location) 'venv\cloudflared.exe'

# A terminal opened before the install doesn't have cloudflared on its PATH yet
function Find-Cloudflared {
    $found = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
    if ($found) { return $found }
    "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe", "$env:ProgramFiles\cloudflared\cloudflared.exe", $localCopy |
        Where-Object { Test-Path $_ } | Select-Object -First 1
}

$cloudflared = Find-Cloudflared
if (-not $cloudflared -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host 'cloudflared is not installed; installing it with winget (accept the prompt if Windows asks)...'
    winget install --id Cloudflare.cloudflared -e --silent --accept-source-agreements --accept-package-agreements
    $cloudflared = Find-Cloudflared
}
if (-not $cloudflared) {
    # No winget, or the install failed: fetch the standalone exe, no admin rights needed
    Write-Host 'Downloading cloudflared from github.com/cloudflare/cloudflared...'
    $arch = if ([Environment]::Is64BitOperatingSystem) { 'amd64' } else { '386' }
    $ProgressPreference = 'SilentlyContinue'   # the progress bar makes Invoke-WebRequest very slow
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    try {
        Invoke-WebRequest -UseBasicParsing -OutFile "$localCopy.part" `
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-$arch.exe"
        Move-Item -Force "$localCopy.part" $localCopy
        $cloudflared = $localCopy
    } catch {
        Remove-Item "$localCopy.part" -ErrorAction SilentlyContinue
        throw "Could not get cloudflared ($_). Install it by hand with: winget install Cloudflare.cloudflared"
    }
}

$server = Start-Process -PassThru -NoNewWindow venv\Scripts\waitress-serve.exe `
    -ArgumentList '--listen=127.0.0.1:8000', '--call', 'eshop:create_app'
try {
    & $cloudflared tunnel --url http://127.0.0.1:8000   # prints https://<random>.trycloudflare.com
} finally {
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
}
