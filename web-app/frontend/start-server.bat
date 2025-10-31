@echo off
REM Start frontend web server on IP address để người khác có thể truy cập
REM Usage: start-server.bat [port]
REM Default port: 8080

set PORT=%1
if "%PORT%"=="" set PORT=8080

echo ========================================
echo Starting Frontend Server
echo ========================================
echo.
echo Server will be accessible at:
echo   - http://localhost:%PORT%
echo   - http://YOUR_IP_ADDRESS:%PORT%
echo.
echo To find your IP address, run: ipconfig
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

cd /d "%~dp0"
python -m http.server %PORT% --bind 0.0.0.0

