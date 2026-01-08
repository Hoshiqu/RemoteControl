#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автономный HTTP сервер для удаленного управления питанием компьютера
Обновленная версия с поддержкой активных задач
"""

import subprocess
import sys
import os
import time
import logging
from flask import Flask, request, jsonify, send_from_directory
import threading
from datetime import datetime, timedelta
import uuid

# Настройка логирования
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'power_server.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # Добавляем вывод в консоль для отладки
    ]
)

app = Flask(__name__)

# Скрыть окно консоли в Windows (отключаем для отладки)
# if os.name == 'nt':
#     try:
#         import ctypes
#         ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
#     except:
#         pass

# Словарь для хранения активных задач
active_tasks = {}
# Блокировка для предотвращения одновременного выполнения нескольких команд
command_lock = threading.Lock()

def cleanup_completed_tasks():
    """Очистка завершенных задач"""
    try:
        current_time = datetime.now()
        completed_tasks = []
        
        for task_id, task in list(active_tasks.items()):
            try:
                elapsed = (current_time - task['start_time']).total_seconds()
                if elapsed >= task['delay']:
                    completed_tasks.append(task_id)
            except Exception as e:
                logging.error(f"Ошибка при проверке задачи {task_id}: {e}")
                # Добавляем проблемную задачу в список на удаление
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            if task_id in active_tasks:
                logging.info(f"Удаление завершенной/проблемной задачи {task_id}")
                del active_tasks[task_id]
                
    except Exception as e:
        logging.error(f"Критическая ошибка в cleanup_completed_tasks: {e}")
        # В крайнем случае очищаем все задачи
        active_tasks.clear()
        logging.warning("Очищены все задачи из-за критической ошибки")

def execute_power_command(command, delay=3):
    """Выполнение команд управления питанием"""
    
    try:
        task_id = str(uuid.uuid4())
        logging.info(f"Получена команда: {command}, задержка: {delay}с, ID: {task_id}")
        
        # Создаем событие для возможности отмены
        cancel_event = threading.Event()
        
        def delayed_execution():
            try:
                # Ждем указанное время, проверяя флаг отмены каждую секунду
                for second in range(delay):
                    if cancel_event.is_set():
                        logging.info(f"Команда {command} (ID: {task_id}) была отменена")
                        return
                    time.sleep(1)
                
                # Если команда не была отменена, выполняем её
                if not cancel_event.is_set():
                    commands = {
                        'shutdown': ['shutdown', '/s', '/f', '/t', '0'],
                        'restart': ['shutdown', '/r', '/f', '/t', '0'],
                        'hibernate': ['shutdown', '/h'],
                        'sleep': ['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'],
                        'lock': ['rundll32.exe', 'user32.dll,LockWorkStation']
                    }
                    
                    if command in commands:
                        try:
                            subprocess.run(commands[command], timeout=30)
                            logging.info(f"Команда {command} (ID: {task_id}) выполнена успешно")
                        except Exception as e:
                            logging.error(f"Ошибка при выполнении {command} (ID: {task_id}): {e}")
            finally:
                # Удаляем задачу из активных
                if task_id in active_tasks:
                    logging.info(f"Удаление выполненной задачи {task_id}")
                    del active_tasks[task_id]
        
        # Запускаем поток для выполнения команды
        thread = threading.Thread(target=delayed_execution)
        thread.daemon = True
        thread.start()
        
        # Сохраняем информацию о задаче
        active_tasks[task_id] = {
            'command': command,
            'delay': delay,
            'start_time': datetime.now(),
            'cancel_event': cancel_event,
            'thread': thread
        }
        
        return task_id, None
        
    except Exception as e:
        logging.error(f"Ошибка в execute_power_command: {e}")
        return None, f"Ошибка: {str(e)}"

@app.route('/cancel/<task_id>', methods=['GET', 'POST'])
def cancel_task(task_id):
    """Отмена запланированной команды"""
    client_ip = request.environ.get('REMOTE_ADDR', 'Unknown')
    logging.info(f"Запрос на отмену задачи {task_id} от {client_ip}")
    
    if task_id in active_tasks:
        task = active_tasks[task_id]
        task['cancel_event'].set()  # Устанавливаем флаг отмены
        
        # Удаляем задачу из активных
        del active_tasks[task_id]
        
        logging.info(f"Задача {task_id} ({task['command']}) отменена")
        
        return jsonify({
            "status": "success",
            "message": f"Команда {task['command']} отменена",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Задача не найдена или уже выполнена",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }), 404

@app.route('/active_tasks', methods=['GET', 'POST'])
def get_active_tasks():
    """Получение списка активных задач"""
    client_ip = request.environ.get('REMOTE_ADDR', 'Unknown')
    logging.info(f"Запрос на получение активных задач от {client_ip}")
    
    try:
        # Очищаем завершенные задачи
        cleanup_completed_tasks()
        
        tasks_info = []
        current_time = datetime.now()
        
        for task_id, task in list(active_tasks.items()):
            try:
                elapsed = (current_time - task['start_time']).total_seconds()
                remaining = max(0, task['delay'] - elapsed)
                
                # Если задача уже должна быть выполнена, пропускаем её
                if remaining <= 0:
                    continue
                    
                tasks_info.append({
                    "task_id": task_id,
                    "command": task['command'],
                    "remaining_seconds": int(remaining),
                    "total_delay": task['delay'],
                    "start_time": task['start_time'].isoformat(),
                    "execute_time": (task['start_time'] + 
                                   timedelta(seconds=task['delay'])).isoformat()
                })
            except Exception as e:
                logging.error(f"Ошибка при обработке задачи {task_id}: {e}")
                # Удаляем проблемную задачу
                if task_id in active_tasks:
                    del active_tasks[task_id]
                continue
        
        # Сортируем по времени выполнения
        tasks_info.sort(key=lambda x: x['remaining_seconds'])
        
        return jsonify({
            "status": "success",
            "active_tasks": tasks_info,
            "count": len(tasks_info),
            "timestamp": current_time.isoformat()
        })
    
    except Exception as e:
        logging.error(f"Критическая ошибка в get_active_tasks: {e}")
        return jsonify({
            "status": "error",
            "message": f"Ошибка сервера: {str(e)}",
            "active_tasks": [],
            "count": 0,
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    """Выключение компьютера"""
    client_ip = request.environ.get('REMOTE_ADDR', 'Unknown')
    delay = request.args.get('delay', 5, type=int)
    logging.info(f"Запрос на выключение от {client_ip}, задержка: {delay}с")
    
    task_id, error = execute_power_command('shutdown', delay)
    if task_id:
        return jsonify({
            "status": "success",
            "command": "shutdown",
            "message": f"Компьютер будет выключен через {delay} секунд",
            "task_id": task_id,
            "delay": delay,
            "timestamp": datetime.now().isoformat()
        })
    return jsonify({
        "status": "error", 
        "command": "shutdown",
        "message": error or "Не удалось выполнить команду"
    }), 500

@app.route('/restart', methods=['GET', 'POST'])
def restart():
    """Перезагрузка компьютера"""
    client_ip = request.environ.get('REMOTE_ADDR', 'Unknown')
    delay = request.args.get('delay', 5, type=int)
    logging.info(f"Запрос на перезагрузку от {client_ip}, задержка: {delay}с")
    
    task_id, error = execute_power_command('restart', delay)
    if task_id:
        return jsonify({
            "status": "success",
            "command": "restart",
            "message": f"Компьютер будет перезагружен через {delay} секунд",
            "task_id": task_id,
            "delay": delay,
            "timestamp": datetime.now().isoformat()
        })
    return jsonify({
        "status": "error", 
        "command": "restart",
        "message": error or "Не удалось выполнить команду"
    }), 500

@app.route('/sleep', methods=['GET', 'POST'])
def sleep():
    """Перевод в режим сна"""
    client_ip = request.environ.get('REMOTE_ADDR', 'Unknown')
    delay = request.args.get('delay', 3, type=int)
    logging.info(f"Запрос на сон от {client_ip}, задержка: {delay}с")
    
    task_id, error = execute_power_command('sleep', delay)
    if task_id:
        return jsonify({
            "status": "success",
            "command": "sleep",
            "message": f"Компьютер перейдет в режим сна через {delay} секунд",
            "task_id": task_id,
            "delay": delay,
            "timestamp": datetime.now().isoformat()
        })
    return jsonify({
        "status": "error", 
        "command": "sleep",
        "message": error or "Не удалось выполнить команду"
    }), 500

@app.route('/hibernate', methods=['GET', 'POST'])
def hibernate():
    """Перевод в режим гибернации"""
    client_ip = request.environ.get('REMOTE_ADDR', 'Unknown')
    delay = request.args.get('delay', 3, type=int)
    logging.info(f"Запрос на гибернацию от {client_ip}, задержка: {delay}с")
    
    task_id, error = execute_power_command('hibernate', delay)
    if task_id:
        return jsonify({
            "status": "success",
            "command": "hibernate",
            "message": f"Компьютер перейдет в режим гибернации через {delay} секунд",
            "task_id": task_id,
            "delay": delay,
            "timestamp": datetime.now().isoformat()
        })
    return jsonify({
        "status": "error", 
        "command": "hibernate",
        "message": error or "Не удалось выполнить команду"
    }), 500

@app.route('/lock', methods=['GET', 'POST'])
def lock():
    """Блокировка компьютера"""
    client_ip = request.environ.get('REMOTE_ADDR', 'Unknown')
    delay = request.args.get('delay', 1, type=int)
    logging.info(f"Запрос на блокировку от {client_ip}, задержка: {delay}с")
    
    task_id, error = execute_power_command('lock', delay)
    if task_id:
        return jsonify({
            "status": "success",
            "command": "lock",
            "message": f"Компьютер будет заблокирован через {delay} секунд",
            "task_id": task_id,
            "delay": delay,
            "timestamp": datetime.now().isoformat()
        })
    return jsonify({
        "status": "error", 
        "command": "lock",
        "message": error or "Не удалось выполнить команду"
    }), 500

@app.route('/status', methods=['GET'])
def status():
    """Проверка статуса сервера"""
    try:
        cleanup_completed_tasks()  # Очищаем при каждом запросе статуса
        
        return jsonify({
            "status": "online",
            "message": "Сервер управления питанием работает",
            "commands": ["/shutdown", "/restart", "/sleep", "/hibernate", "/lock"],
            "management": ["/cancel/<task_id>", "/active_tasks"],
            "active_tasks_count": len(active_tasks),
            "server_version": "3.0",
            "usage": "Добавьте ?delay=X для установки задержки в секундах",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Ошибка в /status: {e}")
        return jsonify({
            "status": "online",  # Сервер работает, даже если есть проблемы с задачами
            "message": "Сервер работает с ограничениями",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

@app.route('/', methods=['GET'])
def index():
    """Главная страница"""
    cleanup_completed_tasks()
    
    return jsonify({
        "name": "Power Management Server Pro",
        "version": "3.0",
        "status": "online",
        "endpoints": {
            "/status": "Статус сервера",
            "/shutdown": "Выключение компьютера", 
            "/restart": "Перезагрузка",
            "/sleep": "Режим сна",
            "/hibernate": "Режим гибернации",
            "/lock": "Блокировка экрана",
            "/cancel/<task_id>": "Отмена команды",
            "/active_tasks": "Список активных задач",
            "/debug": "Отладочная информация"
        },
        "active_tasks": len(active_tasks),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/debug', methods=['GET'])
def debug_info():
    """Отладочная информация"""
    try:
        return jsonify({
            "status": "success",
            "active_tasks_raw": active_tasks,
            "active_tasks_count": len(active_tasks),
            "server_time": datetime.now().isoformat(),
            "python_version": sys.version,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/mobile_control.html', methods=['GET'])
def mobile_control():
    """Мобильный интерфейс"""
    return send_from_directory('.', 'mobile_control.html')

@app.route('/icons/<path:filename>')
def icons(filename):
    """
    Отдаёт любой файл из папки ./icons по URL /icons/<filename>
    """
    icons_dir = os.path.join(app.root_path, 'icons')
    return send_from_directory(icons_dir, filename)

# Настройка статических файлов
app.static_folder = '.'

# Добавляем обработку CORS и оптимизацию соединений
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Connection,Keep-Alive')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    
    # Оптимизация соединений
    response.headers.add('Connection', 'keep-alive')
    response.headers.add('Keep-Alive', 'timeout=30, max=1000')
    
    # Кэширование для статических ресурсов
    if request.endpoint in ['status', 'index']:
        response.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
    
    return response

# Фоновая задача для очистки завершенных задач
def background_cleanup():
    """Фоновая очистка завершенных задач каждые 30 секунд"""
    while True:
        time.sleep(30)
        cleanup_completed_tasks()

if __name__ == '__main__':
    try:
        # Запускаем фоновую очистку
        cleanup_thread = threading.Thread(target=background_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        # Определяем IP адрес автоматически
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        logging.info("=" * 60)
        logging.info("🚀 Запуск сервера управления питанием Pro v3.0")
        logging.info(f"📡 Сервер доступен по адресу: http://{local_ip}:8000")
        logging.info("📋 Доступные команды:")
        logging.info("   • /shutdown, /restart, /sleep, /hibernate, /lock")
        logging.info("   • /cancel/<task_id>, /active_tasks, /status, /debug")
        logging.info("💡 Новые возможности:")
        logging.info("   • Отслеживание активных задач")
        logging.info("   • Автоматическая очистка завершенных команд")
        logging.info("   • Улучшенное логирование и обработка ошибок")
        logging.info("   • Отладочный эндпоинт /debug")
        logging.info("   • Оптимизация HTTP-соединений (keep-alive)")
        logging.info("=" * 60)
        
        print(f"🚀 Сервер запущен на http://{local_ip}:8000")
        print("📱 Для остановки нажмите Ctrl+C")
        print("💡 Оптимизирован для минимального количества соединений")
        print("📌 Если много TIME_WAIT соединений, перезапустите сервер")
        
        # Настройки для оптимизации соединений
        from werkzeug.serving import WSGIRequestHandler
        WSGIRequestHandler.protocol_version = "HTTP/1.1"
        
        app.run(
            host='0.0.0.0',  # Слушаем на всех интерфейсах
            port=8000,
            debug=False,
            use_reloader=False,
            threaded=True,
            # Оптимизация для keep-alive соединений
            processes=1,
            ssl_context=None
        )
    except Exception as e:
        logging.error(f"❌ Критическая ошибка при запуске сервера: {e}")
        print(f"❌ Ошибка запуска: {e}")
        input("Нажмите Enter для выхода...")
        sys.exit(1)