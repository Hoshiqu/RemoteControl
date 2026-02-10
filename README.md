# Power Management Server

Простой HTTP-сервер для удаленного управления питанием Windows-компьютера через веб-интерфейс.

![Версия](https://img.shields.io/badge/Версия-2.1-blue)
![Платформа](https://img.shields.io/badge/Платформа-Windows-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-yellow)

## 🚀 Возможности

- 🔌 Удаленное выключение компьютера
- 🔄 Перезагрузка
- 💤 Перевод в режим сна/гибернации
- 🔒 Блокировка экрана
- 📱 Удобный мобильный интерфейс
- 🔧 Автозапуск при входе в систему
- 🛡️ Настройка брандмауэра
- 🧩 Простая установка одной командой
- ⏹️ Возможность отмены команд до их выполнения

## 📋 Требования

- Windows 10/11
- Python 3.8+
- Права администратора (для установки)

## ⚡ Быстрая установка

Запустите PowerShell от имени администратора и выполните:

```powershell
iex (iwr -UseBasicParsing https://raw.githubusercontent.com/USERNAME/PowerServer/main/install.ps1)
```

Или скачайте репозиторий и выполните:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

## 🔧 Ручная установка

1. Клонируйте репозиторий:
   ```
   git clone https://github.com/USERNAME/PowerServer.git C:\PowerServer
   ```

2. Перейдите в директорию:
   ```
   cd C:\PowerServer
   ```

3. Создайте виртуальное окружение:
   ```
   python -m venv power_server_env
   ```

4. Активируйте окружение:
   ```
   power_server_env\Scripts\activate
   ```

5. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```

6. Запустите скрипт настройки:
   ```
   powershell -ExecutionPolicy Bypass -File setup_silent_autostart.ps1
   ```

## 📱 Использование

После установки сервер будет доступен по адресу:
- Локальный доступ: http://localhost:8000
- Мобильный интерфейс: http://localhost:8000/mobile_control.html
- Из локальной сети: http://[IP-адрес]:8000

### API Endpoints

| Endpoint | Описание | Параметры |
|----------|----------|-----------|
| /status | Проверка статуса сервера | - |
| /shutdown | Выключение компьютера | ?delay=секунды |
| /restart | Перезагрузка компьютера | ?delay=секунды |
| /sleep | Перевод в режим сна | ?delay=секунды |
| /hibernate | Перевод в режим гибернации | ?delay=секунды |
| /lock | Блокировка экрана | ?delay=секунды |
| /active_tasks | Список активных задач | - |
| /cancel/\<task_id\> | Отмена задачи | - |

## 🛠️ Управление

### Команды PowerShell

- Запуск сервера: `Start-ScheduledTask -TaskName 'PowerServerUser'`
- Остановка сервера: `Stop-ScheduledTask -TaskName 'PowerServerUser'`
- Просмотр логов: `Get-Content C:\PowerServer\startup.log -Tail 10`

### Ручной запуск

Запустите файл `hidden_start.vbs` в директории установки.

## 📄 Лицензия

MIT License

## 🔒 Безопасность

Сервер не имеет встроенной аутентификации. Рекомендуется использовать только в защищенных локальных сетях или настроить дополнительную защиту. 