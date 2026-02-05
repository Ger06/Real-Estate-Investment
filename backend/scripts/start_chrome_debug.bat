@echo off
REM ============================================================
REM Inicia Chrome con remote debugging para el scraper de ML.
REM Mata cualquier Chrome en background antes de arrancar.
REM ============================================================

set DEBUG_PORT=9222

REM Buscar Chrome en ubicaciones comunes
set CHROME_PATH=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
) else if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
) else if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%LocalAppData%\Google\Chrome\Application\chrome.exe"
)

if "%CHROME_PATH%"=="" (
    echo ERROR: No se encontro Chrome.
    pause
    exit /b 1
)

echo Cerrando todas las instancias de Chrome...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Iniciando Chrome con debugging en puerto %DEBUG_PORT%...
start "" "%CHROME_PATH%" --remote-debugging-port=%DEBUG_PORT%
timeout /t 3 /nobreak >nul

REM Verificar que el puerto esta abierto
powershell -Command "try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', %DEBUG_PORT%); $c.Close(); Write-Host 'OK: Puerto %DEBUG_PORT% abierto. Chrome listo para scraping.' } catch { Write-Host 'ERROR: Puerto %DEBUG_PORT% no responde. Algo fallo.' }"

echo.
echo Ahora podes ejecutar el scraper de MercadoLibre.
pause
