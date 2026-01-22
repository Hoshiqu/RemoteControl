@echo off
cd /d "C:\PowerServer"

echo %date% %time% - Starting user mode server >> startup.log

taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
timeout /t 3 /nobreak >nul

if exist "power_server_env\Scripts\activate.bat" (
    call power_server_env\Scripts\activate.bat
    echo %date% %time% - Virtual environment activated >> startup.log
)

echo %date% %time% - Starting server >> startup.log
start /b pythonw.exe power_management_server.py

timeout /t 15 /nobreak >nul

echo %date% %time% - Startup completed >> startup.log
exit /b 0
