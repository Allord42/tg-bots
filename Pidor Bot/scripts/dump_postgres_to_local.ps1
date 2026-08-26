$ErrorActionPreference = "Stop"
$env:Path = "C:\Program Files\heroku\bin;" + $env:Path
$Root = "D:\Programming\Projects\Telegram bots"
$Bot = Join-Path $Root "Pidor Bot"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Script = Join-Path $Bot "scripts\dump_postgres_to_local.py"
$env:PYTHONPATH = $Bot
Set-Location $Bot
& $Python $Script
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
