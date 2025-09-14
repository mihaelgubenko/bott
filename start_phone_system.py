#!/usr/bin/env python3
"""
Запуск полной системы телефонного автоответчика
"""
import subprocess
import time
import sys
import os
import webbrowser
from pathlib import Path

def check_ollama():
    """Проверяем что Ollama запущен"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """Запускаем Ollama если не запущен"""
    ollama_path = r'C:\Users\mihae\AppData\Local\Programs\Ollama\ollama.exe'
    
    if not os.path.exists(ollama_path):
        print("❌ Ollama не найден. Установите Ollama сначала.")
        return False
    
    print("🚀 Запускаем Ollama...")
    try:
        subprocess.Popen([ollama_path, 'serve'], 
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # Ждем запуска
        for i in range(10):
            time.sleep(2)
            if check_ollama():
                print("✅ Ollama запущен!")
                return True
            print(f"⏳ Ждем Ollama... ({i+1}/10)")
        
        print("❌ Ollama не запустился за 20 секунд")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка запуска Ollama: {e}")
        return False

def install_dependencies():
    """Устанавливаем зависимости"""
    print("📦 Проверяем зависимости...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'websockets', 'requests'], 
                      check=True, capture_output=True)
        print("✅ Зависимости установлены")
        return True
    except Exception as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def start_phone_server():
    """Запускаем WebSocket сервер"""
    print("📞 Запускаем телефонный сервер...")
    try:
        return subprocess.Popen([sys.executable, 'phone_server.py'])
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        return None

def main():
    print("🎯 Запуск системы AI автоответчика")
    print("=" * 50)
    
    # Проверяем текущую директорию
    current_dir = Path.cwd()
    print(f"📁 Рабочая директория: {current_dir}")
    
    # Проверяем файлы
    required_files = ['phone_server.py', 'website/phone_test.html']
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Файл не найден: {file_path}")
            return
    
    print("✅ Все необходимые файлы найдены")
    
    # Устанавливаем зависимости
    if not install_dependencies():
        return
    
    # Проверяем/запускаем Ollama
    if not check_ollama():
        print("⚠️ Ollama не запущен")
        if not start_ollama():
            print("❌ Не удалось запустить Ollama")
            print("💡 Попробуйте запустить вручную: ollama serve")
            return
    else:
        print("✅ Ollama уже запущен")
    
    # Запускаем телефонный сервер
    server_process = start_phone_server()
    if not server_process:
        return
    
    # Ждем запуска сервера
    print("⏳ Ждем запуска сервера...")
    time.sleep(3)
    
    # Открываем веб-интерфейс
    test_page = Path("website/phone_test.html").absolute()
    print(f"🌐 Открываем тестовый интерфейс: {test_page}")
    
    try:
        webbrowser.open(f"file:///{test_page}")
    except Exception as e:
        print(f"⚠️ Не удалось открыть браузер: {e}")
        print(f"📝 Откройте вручную: file:///{test_page}")
    
    print("\n" + "=" * 50)
    print("🎉 Система запущена!")
    print("📞 WebSocket сервер: ws://localhost:8765")
    print("🌐 Тестовый интерфейс открыт в браузере")
    print("\n💡 Инструкции:")
    print("1. В браузере нажмите 'Подключиться'")
    print("2. Нажмите 'Начать звонок'")
    print("3. Введите сообщение и отправьте")
    print("4. Получите ответ от AI")
    print("\n⏹️ Для остановки нажмите Ctrl+C")
    
    try:
        # Ждем прерывания
        server_process.wait()
    except KeyboardInterrupt:
        print("\n👋 Останавливаем систему...")
        server_process.terminate()
        print("✅ Система остановлена")

if __name__ == "__main__":
    main()
