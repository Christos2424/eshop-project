# Serves the shop from this PC and gives it a temporary public HTTPS address.
# Needs cloudflared once:  winget install Cloudflare.cloudflared
# Run from the flask_eshop folder:  powershell -ExecutionPolicy Bypass -File deploy\start_public.ps1
# Stop with Ctrl+C (the public address stops working when this window closes).

$env:SESSION_COOKIE_SECURE = '1'   # the tunnel serves HTTPS

# A terminal opened before the install doesn't have cloudflared on its PATH yet
$cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cloudflared) {
    $cloudflared = "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe", "$env:ProgramFiles\cloudflared\cloudflared.exe" |
        Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $cloudflared) { throw 'cloudflared not found. Install it with: winget install Cloudflare.cloudflared' }

$server = Start-Process -PassThru -NoNewWindow venv\Scripts\waitress-serve.exe `
    -ArgumentList '--listen=127.0.0.1:8000', '--call', 'eshop:create_app'
try {
    & $cloudflared tunnel --url http://127.0.0.1:8000   # prints https://<random>.trycloudflare.com
} finally {
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
}
