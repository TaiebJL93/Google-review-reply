<#
.SYNOPSIS
  Deploys ReviewReply to Cloudflare Containers (https://reviewreply.<subdomain>.workers.dev).

.DESCRIPTION
  1. Checks Docker is running (wrangler builds the image locally).
  2. Installs the Worker's npm packages in cloudflare/.
  3. Signs in to Cloudflare with `wrangler login` if needed (browser "Allow" click).
  4. Asks for any missing secret and stores it with `wrangler secret put`.
     Values are read hidden and sent straight to Cloudflare; nothing is written to disk.
  5. Runs `wrangler deploy`.

  Needs the Workers Paid plan and a Neon Postgres connection string. See README.md,
  "Hosting on Cloudflare (Containers)".

.PARAMETER SetSecrets
  Ask for every secret again, even ones already stored on Cloudflare.
#>
param([switch]$SetSecrets)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$workerDir = Join-Path $root "cloudflare"
Set-Location $workerDir

function Invoke-Wrangler {
    & npx --yes wrangler @args
    if ($LASTEXITCODE -ne 0) { throw "wrangler $($args -join ' ') failed (exit $LASTEXITCODE)." }
}

# 1. Docker
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker isn't running. Start Rancher Desktop (container engine: dockerd/moby), wait until it's ready, then run this again."
}

# 2. npm packages
if (-not (Test-Path (Join-Path $workerDir "node_modules"))) {
    Write-Host "Installing Worker packages ..."
    npm install --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { throw "npm install failed." }
}

# 3. Cloudflare sign-in
& npx --yes wrangler whoami *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Signing in to Cloudflare - a browser tab will open; click Allow."
    Invoke-Wrangler login
}

# 4. Secrets
$existing = @()
$listJson = & npx --yes wrangler secret list --format json 2>$null
if ($LASTEXITCODE -eq 0 -and $listJson) {
    $existing = ($listJson | Out-String | ConvertFrom-Json) | ForEach-Object { $_.name }
}

$secrets = [ordered]@{
    GEMINI_API_KEY       = "Gemini API key (https://aistudio.google.com/apikey)"
    DATABASE_URL         = "Neon Postgres connection string (postgresql://...)"
    SECRET_KEY           = "Session signing key (leave empty to generate a random one)"
    GOOGLE_CLIENT_ID     = "Google OAuth client ID (leave empty to skip Connect Google)"
    GOOGLE_CLIENT_SECRET = "Google OAuth client secret (leave empty to skip)"
    GOOGLE_REDIRECT_URI  = "Google OAuth callback URL (leave empty to skip; set after first deploy)"
}
$required = @("GEMINI_API_KEY", "DATABASE_URL")

foreach ($name in $secrets.Keys) {
    if (-not $SetSecrets -and $existing -contains $name) { continue }

    $secure = Read-Host -Prompt "$name - $($secrets[$name])" -AsSecureString
    $value = [System.Net.NetworkCredential]::new("", $secure).Password

    if (-not $value -and $name -eq "SECRET_KEY") {
        $bytes = New-Object byte[] 32
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        $value = [Convert]::ToBase64String($bytes)
        Write-Host "  generated a random SECRET_KEY"
    }
    if (-not $value) {
        if ($required -contains $name) { throw "$name is required." }
        continue
    }

    $value | & npx --yes wrangler secret put $name
    if ($LASTEXITCODE -ne 0) { throw "Storing $name failed." }
    $value = $null
}

# 5. Deploy
Write-Host "Deploying (builds the Docker image and uploads it; the first run takes a few minutes) ..."
Invoke-Wrangler deploy

Write-Host ""
Write-Host "Done. Open the workers.dev URL printed above." -ForegroundColor Green
Write-Host "After the very first deploy, give Cloudflare a few minutes before the container answers."
