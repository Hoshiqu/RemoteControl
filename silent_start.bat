@echo off
cd /d "C:\PowerServer"
echo %date% %time% - === USER MODE STARTUP === >> startup.log
echo %date% %time% - Current user: %USERNAME% >> startup.log

REM Kill all Python processes
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
timeout /t 3 /nobreak >nul

REM Activate virtual environment (works for user)
if exist "power_server_env\Scripts\activate.bat" (
    echo %date% %time% - Activating virtual environment >> startup.log
    call power_server_env\Scripts\activate.bat
    
    echo %date% %time% - Testing Python access >> startup.log
    python.exe --version >> startup.log 2>&1
    
    echo %date% %time% - Starting server >> startup.log
    start /b pythonw.exe power_management_server.py
    
    timeout /t 15 /nobreak >nul
    
    echo %date% %time% - Testing connectivity >> startup.log
    powershell -Command "try { Invoke-WebRequest 'http://localhost:8000/status' -TimeoutSec 5 -UseBasicParsing | Out-Null; 'SUCCESS' } catch { 'FAILED' }" >> startup.log 2>&1
    
) else (
    echo %date% %time% - ERROR: Virtual environment not found >> startup.log
    exit /b 1
)

echo %date% %time% - === USER STARTUP COMPLETED === >> startup.log
exit /b 0