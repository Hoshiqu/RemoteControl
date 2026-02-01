# Power Management Server - Установка одной командой
# Запустите от имени администратора
# Использование: 
# powershell -ExecutionPolicy Bypass -File install.ps1 [DestinationPath]

param (
    [string]$DestinationPath = "C:\PowerServer"
)

$ErrorActionPreference = "Stop"
$repo = "https://github.com/USERNAME/PowerServer"

function Write-ColorText {
    param (
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

Write-ColorText "=== Power Management Server - Установка ===" "Green"
Write-ColorText "Репозиторий: $repo" "Cyan"
Write-ColorText "Путь установки: $DestinationPath" "Cyan"

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-NOT $isAdmin) {
    Write-ColorText "ОШИБКА: Запустите скрипт от имени администратора!" "Red"
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Создание директории, если не существует
if (-NOT (Test-Path $DestinationPath)) {
    Write-ColorText "Создание директории $DestinationPath..." "Yellow"
    New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
}

# Загрузка файлов из репозитория
Write-ColorText "Загрузка файлов из репозитория..." "Yellow"

try {
    # Создание временной директории
    $tempDir = Join-Path $env:TEMP "PowerServerTemp"
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    # Загрузка архива с GitHub
    $zipUrl = "$repo/archive/main.zip"
    $zipFile = Join-Path $tempDir "PowerServer.zip"
    
    Write-ColorText "Загрузка архива с GitHub..." "Yellow"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -UseBasicParsing
    
    # Распаковка архива
    Write-ColorText "Распаковка архива..." "Yellow"
    Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
    
    # Копирование файлов
    $extractedDir = Get-ChildItem -Path $tempDir -Directory | Select-Object -First 1
    Write-ColorText "Копирование файлов в $DestinationPath..." "Yellow"
    Copy-Item -Path "$($extractedDir.FullName)\*" -Destination $DestinationPath -Recurse -Force
    
    # Очистка
    Remove-Item -Path $tempDir -Recurse -Force
} catch {
    Write-ColorText "Ошибка при загрузке файлов: $_" "Red"
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Переход в директорию установки
Set-Location $DestinationPath

# Настройка Python и виртуального окружения
Write-ColorText "Настройка Python и виртуального окружения..." "Yellow"

try {
    # Проверка наличия Python
    $pythonInstalled = $false
    try {
        $pythonVersion = python --version
        $pythonInstalled = $true
        Write-ColorText "Найден Python: $pythonVersion" "Green"
    } catch {
        Write-ColorText "Python не найден. Пожалуйста, установите Python 3.8+ и запустите скрипт снова." "Red"
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }

    # Создание виртуального окружения
    if (-NOT (Test-Path "power_server_env")) {
        Write-ColorText "Создание виртуального окружения..." "Yellow"
        python -m venv power_server_env
    }

    # Активация виртуального окружения и установка зависимостей
    Write-ColorText "Установка зависимостей..." "Yellow"
    & power_server_env\Scripts\activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

} catch {
    Write-ColorText "Ошибка при настройке Python: $_" "Red"
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Запуск скрипта настройки автозапуска
Write-ColorText "Настройка автозапуска..." "Yellow"
try {
    & .\setup_silent_autostart.ps1
} catch {
    Write-ColorText "Ошибка при настройке автозапуска: $_" "Red"
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-ColorText "`nУстановка завершена успешно!" "Green"
Write-ColorText "Сервер доступен по адресу: http://localhost:8000" "Cyan"
Write-ColorText "Мобильный интерфейс: http://localhost:8000/mobile_control.html" "Cyan"
Write-ColorText "`nСервер будет автоматически запускаться при входе в систему." "Green"

Read-Host "Нажмите Enter для завершения" 