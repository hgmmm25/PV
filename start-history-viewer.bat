@echo off
chcp 65001 >nul 2>&1
title AI Video History Viewer

echo.
echo  ============================================
echo    AI Video History Viewer
echo  ============================================
echo.

:: -- Step 1: Navigate to viewer directory --
cd /d "%~dp0history-viewer"

:: -- Step 2: Install dependencies if needed --
if not exist "node_modules\" (
    echo  [1/3] Installing npm dependencies...
    call npm install
    if errorlevel 1 (
        echo.
        echo  X npm install failed. Is Node.js installed?
        echo    Download: https://nodejs.org/
        pause
        exit /b 1
    )
    echo.
)

:: -- Step 3: Create node_modules symlink at project root --
::    (Vite root = D:\PV, needs node_modules accessible there)
cd /d "%~dp0"
if not exist "node_modules\" (
    echo  [2/3] Creating symlink for node_modules...
    mklink /J "node_modules" "history-viewer\node_modules" >nul 2>&1
    if errorlevel 1 (
        echo  ! Could not create junction. Run as Administrator or link manually.
    )
)

:: -- Step 4: Launch Vite dev server --
cd /d "%~dp0history-viewer"
echo  [3/3] Starting Vite dev server...
echo.
echo  ============================================
echo    Local:  http://localhost:3200
echo    Root:   http://localhost:3200/history-viewer/
echo  ============================================
echo.
echo  Press Ctrl+C to stop.
echo.

:: Open browser after short delay
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:3200/history-viewer/"

:: Start Vite (root is set to parent D:\PV via vite.config.js)
call npx vite --port 3200
