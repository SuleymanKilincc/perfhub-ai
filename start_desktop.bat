@echo off
title PerfHub AI v5.0
color 0A

echo.
echo  ==========================================
echo    PerfHub AI v5.0 PRO - Baslatiliyor
echo  ==========================================
echo.

cd /d "%~dp0"

:: Python kontrolu
python --version >nul 2>&1
if errorlevel 1 (
    echo  [HATA] Python bulunamadi! Python PATH'e ekli olmali.
    pause
    exit /b 1
)
echo  [OK] Python bulundu.

:: Bagimlilik kontrolu
python -c "import fastapi, uvicorn, openai" >nul 2>&1
if errorlevel 1 (
    echo  [BILGI] Eksik paketler yukleniyor...
    python -m pip install -r backend\requirements.txt -q
    python -m pip install openai -q
)

:: Port 8000 temizle
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Backend'i arka planda baslat
echo  [1/2] Backend baslatiliyor...
start /B "" python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level error

:: Health check - max 15 saniye bekle
echo  [..] Backend hazir olana kadar bekleniyor...
set tries=0
:wait_loop
timeout /t 1 /nobreak >nul
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)" >nul 2>&1
if not errorlevel 1 goto backend_ready
set /a tries+=1
if %tries% lss 15 goto wait_loop
echo  [UYARI] Backend 15 saniyede yanit vermedi, devam ediliyor...
goto start_gui

:backend_ready
echo  [OK] Backend hazir!

:start_gui
echo  [2/2] Arayuz aciliyor...
echo.
python modern_desktop_app.py

:: Uygulama kapandiktan sonra hata kontrolu
if errorlevel 1 (
    echo.
    echo  ==========================================
    echo  HATA: Uygulama beklenmedik sekilde kapandi!
    echo  Yukardaki hata mesajini not alin.
    echo  ==========================================
    pause
)

:: Backend kapat
echo  Kapatiliyor...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul
