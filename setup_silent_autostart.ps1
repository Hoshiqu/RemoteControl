# Super Simple Power Management Server Setup
# Run as Administrator

Write-Host "=== Simple Power Management Server Setup ===" -ForegroundColor Green

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-NOT $isAdmin) {
    Write-Host "ERROR: Must run as Administrator!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Go to directory
Set-Location "C:\PowerServer"

# Get current user
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Host "Setting up for user: $currentUser" -ForegroundColor Cyan

# Kill existing processes
Write-Host "Killing Python processes..." -ForegroundColor Yellow
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 3

# Remove existing tasks
Write-Host "Removing old tasks..." -ForegroundColor Yellow
Stop-ScheduledTask -TaskName "PowerServer" -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName "PowerServerUser" -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "PowerServer" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "PowerServerUser" -Confirm:$false -ErrorAction SilentlyContinue

# Create simple bat file
Write-Host "Creating startup script..." -ForegroundColor Yellow

$batContent = @"
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
"@

$batContent | Out-File -FilePath "user_start.bat" -Encoding ASCII
Write-Host "Startup script created" -ForegroundColor Green

# Create VBS script to hide console window
Write-Host "Creating hidden launcher..." -ForegroundColor Yellow
$vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\PowerServer\user_start.bat" & Chr(34), 0, False
Set WshShell = Nothing
"@

$vbsContent | Out-File -FilePath "hidden_start.vbs" -Encoding ASCII
Write-Host "Hidden launcher created" -ForegroundColor Green

# Create scheduled task
Write-Host "Creating scheduled task..." -ForegroundColor Yellow

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument """C:\PowerServer\hidden_start.vbs""" -WorkingDirectory "C:\PowerServer"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName "PowerServerUser" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Power Management Server User" -Force | Out-Null

Write-Host "Scheduled task created" -ForegroundColor Green

# Setup firewall
Write-Host "Setting up firewall..." -ForegroundColor Yellow
Remove-NetFirewallRule -DisplayName "PowerServer*" -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "PowerServer-HTTP" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any | Out-Null
Write-Host "Firewall configured" -ForegroundColor Green

# Test the task
Write-Host "Testing task..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName "PowerServerUser"
Write-Host "Waiting 20 seconds..." -ForegroundColor Yellow
Start-Sleep 20

# Check if it worked
$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
Write-Host "Python processes found: $($pythonProcesses.Count)" -ForegroundColor Cyan

# Try to connect to server
Write-Host "Testing server..." -ForegroundColor Yellow
$serverOK = $false
try {
    $response = Invoke-WebRequest "http://localhost:8000/status" -TimeoutSec 5 -UseBasicParsing
    Write-Host "Server is responding!" -ForegroundColor Green
    $serverOK = $true
} catch {
    Write-Host "Server not responding yet" -ForegroundColor Yellow
}

# Test admin command
Write-Host "Testing admin command..." -ForegroundColor Yellow
try {
    $lockTest = Invoke-WebRequest "http://localhost:8000/lock?delay=5" -TimeoutSec 5 -UseBasicParsing
    Write-Host "Admin commands working!" -ForegroundColor Green
} catch {
    Write-Host "Admin command test failed" -ForegroundColor Yellow
}

# Show results
Write-Host ""
Write-Host "=== SETUP COMPLETED ===" -ForegroundColor Green
Write-Host "Task created: PowerServerUser" -ForegroundColor Green
Write-Host "Auto-start: On user login" -ForegroundColor Green
Write-Host "Admin rights: Enabled" -ForegroundColor Green

Write-Host ""
Write-Host "Server URLs:" -ForegroundColor Cyan
Write-Host "  http://localhost:8000" -ForegroundColor White
Write-Host "  http://192.168.1.55:8000" -ForegroundColor White
Write-Host "  http://192.168.1.55:8000/mobile_control.html" -ForegroundColor White

Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  Start: Start-ScheduledTask -TaskName 'PowerServerUser'" -ForegroundColor White
Write-Host "  Stop:  Stop-ScheduledTask -TaskName 'PowerServerUser'" -ForegroundColor White
Write-Host "  Logs:  Get-Content startup.log -Tail 10" -ForegroundColor White

Write-Host ""
Write-Host "Server will start automatically when you login to Windows!" -ForegroundColor Green

Read-Host "Press Enter to finish"