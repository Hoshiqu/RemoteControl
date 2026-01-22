@echo off
cd /d "C:\PowerServer"
call power_server_env\Scripts\activate.bat
start /b pythonw.exe power_management_server.py
