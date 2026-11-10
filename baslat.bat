@echo off
rem Etiket Inceleme Araci: tek tikla baslat (Windows).
rem   baslat.bat                      araci acar
rem   baslat.bat --reviewer ayse      ilk acista kendi adini ver (proje basina kaydedilir)
rem   baslat.bat yenile               arayuzu yeniden derler (kod degistiyse)
rem Ilk calistirmada Python paketlerini ve arayuzu kurar; sonrakilerde dogrudan acar.
rem Arac zaten acik kalmissa (eski pencere) onu kendisi kapatir, boylece her zaman guncel kopya acilir.
rem Gerekenler: Python 3.11/3.12 ve Node.js 20+ (SETUP.md).

cd /d "%~dp0"
setlocal enabledelayedexpansion

where python >nul 2>nul || (echo Python bulunamadi. Python kurulu mu, PATH'e eklendi mi? & pause & exit /b 1)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Python ortami kuruluyor...
  python -m venv .venv || (echo venv kurulamadi & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -q -r server\requirements.txt || (echo pip kurulumu basarisiz & pause & exit /b 1)
)

set REBUILD=
if /i "%~1"=="yenile" (
  set REBUILD=1
  shift
)

if not exist "web\dist\index.html" set REBUILD=1
if defined REBUILD (
  where npm >nul 2>nul || (echo Node.js bulunamadi, arayuz derlenemiyor. https://nodejs.org & pause & exit /b 1)
  echo [2/3] Arayuz derleniyor...
  pushd web
  if not exist "node_modules" call npm install --no-audit --no-fund || (popd & echo npm install basarisiz & pause & exit /b 1)
  call npm run build || (popd & echo derleme basarisiz & pause & exit /b 1)
  popd
)

rem Eski kopya ayni portta calisiyorsa kapat (yoksa yeni kopya acilamaz ve tarayicida eski sayfa gorunur)
set PORT=8000
set PREV=
for %%a in (%*) do (
  if "!PREV!"=="--port" set PORT=%%a
  set PREV=%%a
)
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort !PORT! -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if ($c) { $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $c.OwningProcess); if ($p.CommandLine -match 'server\.py') { Stop-Process -Id $c.OwningProcess -Force; Write-Host 'Acik duran eski arac kapatildi.'; Start-Sleep -Seconds 1 } else { Write-Host 'UYARI: !PORT! portunu baska bir program kullaniyor.' } }"

echo [3/3] Arac aciliyor. Kapatmak icin bu pencerede Ctrl+C.
".venv\Scripts\python.exe" server\server.py --open %1 %2 %3 %4 %5 %6 %7 %8 %9
pause