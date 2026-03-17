@echo off
REM Run Temporal + Discovery worker for F3Next
REM Option 1: Docker (requires Docker Desktop running)
REM Option 2: Temporal CLI (install: winget install temporalio.temporal)

echo.
echo === F3Next Temporal Setup ===
echo.

REM Check for Temporal CLI first (simplest for dev)
where temporal >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [1/2] Starting Temporal server (CLI)...
    start "Temporal Server" cmd /k "temporal server start-dev"
    timeout /t 5 /nobreak >nul
    goto :start_worker
)

REM Fallback: Docker
docker info >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [1/2] Starting Temporal via Docker...
    docker compose -f docker-compose.temporal.yml up -d
    echo Waiting for Temporal to be ready...
    timeout /t 15 /nobreak >nul
    goto :start_worker
)

echo.
echo ERROR: Neither Temporal CLI nor Docker found.
echo.
echo Install one of:
echo   - Temporal CLI: winget install temporalio.temporal
echo   - Docker Desktop: https://www.docker.com/products/docker-desktop
echo.
pause
exit /b 1

:start_worker
echo.
echo [2/2] Starting Discovery worker...
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" -m containers.discovery.worker
pause
