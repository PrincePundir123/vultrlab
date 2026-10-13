param(
    [ValidateSet('start', 'status', 'stop')][string]$Action = 'start',
    [string]$Distribution = 'Ubuntu'
)
$ErrorActionPreference = 'Stop'
$projectDirectory = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
if (-not (Test-Path -LiteralPath (Join-Path $projectDirectory '.env'))) {
    throw 'Create the private .env using infra/scripts/setup_env.py first. See docs/deployment.md.'
}
if ($projectDirectory -notmatch '^([A-Za-z]):\\') {
    throw 'The WSL launcher requires a project on a local Windows drive.'
}
$driveLetter = $Matches[1].ToLowerInvariant()
$linuxDirectory = '/mnt/' + $driveLetter + '/' + $projectDirectory.Substring(3).Replace('\', '/')
& wsl.exe -d $Distribution -u root --cd $linuxDirectory -- bash infra/scripts/local.sh $Action
if ($LASTEXITCODE -ne 0) { throw 'Local Docker command failed. Check WSL, Docker and the initial deployment steps.' }
if ($Action -eq 'start') { Write-Output 'Open http://localhost:8080. Use the operator credentials from your private .env.' }
