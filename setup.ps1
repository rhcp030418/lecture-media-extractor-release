$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 (64-bit), then retry.' }
}
& '.\.venv\Scripts\python.exe' -m ensurepip --upgrade
if ($LASTEXITCODE -ne 0) { throw 'pip installation failed.' }
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.\.venv\Scripts\python.exe' -m lecture_script.runtime
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'GPU setup did not complete. CPU mode remains available. Rerun setup.cmd to retry GPU setup.'
}
& '.\.venv\Scripts\python.exe' install_chrome.py
if ($LASTEXITCODE -ne 0) { throw 'Chrome native host registration failed.' }
Write-Output 'Ready. Open install-guide.html to load the Chrome extension.'
