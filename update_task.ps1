# Обновление задачи PowerServerUser для использования VBS-скрипта
# Запустите от имени администратора

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Host "Обновление задачи для пользователя: $currentUser" -ForegroundColor Cyan

# Остановить существующую задачу
Stop-ScheduledTask -TaskName "PowerServerUser" -ErrorAction SilentlyContinue

# Обновить задачу
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument """C:\PowerServer\hidden_start.vbs""" -WorkingDirectory "C:\PowerServer"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName "PowerServerUser" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Power Management Server User" -Force

Write-Host "Задача обновлена! Теперь cmd не будет показываться при запуске." -ForegroundColor Green
Write-Host "Запуск задачи для проверки..." -ForegroundColor Yellow

Start-ScheduledTask -TaskName "PowerServerUser"
Write-Host "Задача запущена. Проверьте, что сервер работает, открыв http://localhost:8000" -ForegroundColor Green

Read-Host "Нажмите Enter для завершения" 