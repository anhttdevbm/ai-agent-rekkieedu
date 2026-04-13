# Build AgentEdu.exe (one-file, không console) vào dist\
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Không tìm thấy python trên PATH."
}

python -m pip install -e ".[build]"
python scripts/embed_key_from_env.py

# Neu AgentEdu.exe dang chay, PyInstaller khong ghi de duoc (PermissionError).
$p = Get-Process -Name "AgentEdu" -ErrorAction SilentlyContinue
if ($p) {
    Write-Host "Dang tat AgentEdu de build ghi de dist\AgentEdu.exe ..."
    $p | Stop-Process -Force
    Start-Sleep -Milliseconds 800
}

python -m PyInstaller --noconfirm AgentEdu.spec

Write-Host "Xong: dist\AgentEdu.exe"
