<#
.SYNOPSIS
  Runs ReviewReply and publishes it on the internet through a Cloudflare quick tunnel.

.DESCRIPTION
  1. Starts `cloudflared tunnel --url http://localhost:<Port>` and waits for it to print
     its random https://<words>.trycloudflare.com address.
  2. Starts the app with that address wired in (GOOGLE_REDIRECT_URI, Secure cookies).
  3. When you press Ctrl+C the app stops and the tunnel is shut down.

  The address changes every time you run this. See README.md, "Publishing with
  Cloudflare Tunnel", for the limits of quick tunnels.
#>
param(
    [int]$Port = 8000,
    [int]$TunnelTimeoutSeconds = 45
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# --- Locate cloudflared: PATH first, then the per-user folder the README installs into.
$cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cloudflared) {
    $candidate = Join-Path $env:LOCALAPPDATA "cloudflared\cloudflared.exe"
    if (Test-Path $candidate) { $cloudflared = $candidate }
}
if (-not $cloudflared) {
    throw "cloudflared not found. Install it first - see 'Publishing with Cloudflare Tunnel' in README.md."
}

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment not found at .venv. Run the Setup steps in README.md first."
}

# cloudflared writes its log (including the public URL) to stderr.
$outLog = Join-Path $env:TEMP "reviewreply-cloudflared.out.log"
$errLog = Join-Path $env:TEMP "reviewreply-cloudflared.err.log"
Remove-Item $outLog, $errLog -ErrorAction SilentlyContinue

$tunnel = $null
try {
    Write-Host "Starting Cloudflare quick tunnel to http://localhost:$Port ..."
    $tunnel = Start-Process -FilePath $cloudflared `
        -ArgumentList "tunnel", "--url", "http://localhost:$Port" `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
        -WindowStyle Hidden -PassThru

    # (?!api\.) skips the unrelated api.trycloudflare.com host cloudflared also logs.
    $urlPattern = "https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com"
    $publicUrl = $null
    $deadline = (Get-Date).AddSeconds($TunnelTimeoutSeconds)
    while (-not $publicUrl -and (Get-Date) -lt $deadline) {
        if ($tunnel.HasExited) {
            throw "cloudflared exited early. Log: $errLog"
        }
        if (Test-Path $errLog) {
            $match = Select-String -Path $errLog -Pattern $urlPattern | Select-Object -First 1
            if ($match) { $publicUrl = $match.Matches[0].Value }
        }
        if (-not $publicUrl) { Start-Sleep -Milliseconds 500 }
    }
    if (-not $publicUrl) {
        throw "Timed out after $TunnelTimeoutSeconds s waiting for a trycloudflare.com URL. Log: $errLog"
    }

    # Values the app reads at startup (app/config.py). Environment variables win
    # over .env because python-dotenv does not override existing ones.
    $env:GOOGLE_REDIRECT_URI = "$publicUrl/auth/google/callback"
    $env:SECURE_COOKIES = "true"

    Write-Host ""
    Write-Host "ReviewReply is public at:  $publicUrl" -ForegroundColor Green
    Write-Host "Google OAuth callback URL: $env:GOOGLE_REDIRECT_URI"
    Write-Host "  (register that exact URL on your Google OAuth client if you use Connect Google;"
    Write-Host "   it changes every run.)"
    Write-Host "Press Ctrl+C to stop the app and close the tunnel."
    Write-Host ""

    # Bind to loopback only: cloudflared reaches it locally, nothing else on the network needs to.
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port `
        --proxy-headers --forwarded-allow-ips="*"
}
finally {
    if ($tunnel -and -not $tunnel.HasExited) {
        Write-Host "Closing Cloudflare tunnel ..."
        Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
    }
}
