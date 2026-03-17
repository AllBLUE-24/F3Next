# Run backend from repo root or from backend folder. Uses venv if present.
$BackendDir = $PSScriptRoot
$ProjectRoot = Split-Path $BackendDir -Parent
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

$env:PYTHONPATH = $BackendDir
Set-Location $BackendDir
if (Test-Path $VenvPython) {
    & $VenvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} else {
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}
