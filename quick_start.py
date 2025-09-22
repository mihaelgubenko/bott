#!/usr/bin/env python3
"""
Быстрый запуск HR-психоаналитического бота
Автоматически настраивает и запускает бота
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """Проверка зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    required_packages = [
        'python-telegram-bot',
        'openai',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n📦 Установка недостающих пакетов: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ Пакеты установлены!")
        except subprocess.CalledProcessError:
            print("❌ Ошибка установки пакетов")
            return False
    
    return True

def setup_env():
    """Настройка .env файла"""
    print("\n🔧 Настройка .env файла...")
    
    if os.path.exists('.env'):
        print("✅ Файл .env уже существует")
        return True
    
    print("📝 Создание .env файла...")
    
    bot_token = input("Введите BOT_TOKEN: ").strip()
    if not bot_token:
        print("❌ BOT_TOKEN обязателен!")
        return False
    
    openai_key = input("Введите OPENAI_API_KEY: ").strip()
    if not openai_key:
        print("❌ OPENAI_API_KEY обязателен!")
        return False
    
    payment_token = input("Введите PAYMENT_TOKEN (опционально): ").strip()
    
    env_content = f"""# Конфигурация HR-психоаналитического бота
BOT_TOKEN={bot_token}
OPENAI_API_KEY={openai_key}
PAYMENT_TOKEN={payment_token}
DEBUG=False
LOG_LEVEL=INFO
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ Файл .env создан!")
    return True

def choose_bot_version():
    """Выбор версии бота"""
    print("\n🤖 Выберите версию бота:")
    print("1. Простая мобильная версия (рекомендуется)")
    print("2. Полная мобильная версия")
    print("3. Оригинальная версия")
    
    while True:
        choice = input("Введите номер (1-3): ").strip()
        
        if choice == "1":
            return "simple_mobile_bot.py"
        elif choice == "2":
            return "new_hr_bot.py"
        elif choice == "3":
            return "hr_psychoanalyst_bot.py"
        else:
            print("❌ Неверный выбор. Попробуйте снова.")

def start_bot(bot_file):
    """Запуск бота"""
    print(f"\n🚀 Запуск бота: {bot_file}")
    
    if not os.path.exists(bot_file):
        print(f"❌ Файл {bot_file} не найден!")
        return False
    
    try:
        print("✅ Бот запущен! Нажмите Ctrl+C для остановки")
        subprocess.run([sys.executable, bot_file])
        return True
    except KeyboardInterrupt:
        print("\n⏹️  Бот остановлен")
        return True
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        return False

def main():
    """Главная функция"""
    print("🤖 Быстрый запуск HR-психоаналитического бота")
    print("=" * 50)
    
    # Проверка зависимостей
    if not check_dependencies():
        print("❌ Не удалось установить зависимости")
        return
    
    # Настройка .env
    if not setup_env():
        print("❌ Не удалось настроить .env файл")
        return
    
    # Выбор версии бота
    bot_file = choose_bot_version()
    
    # Запуск бота
    if not start_bot(bot_file):
        print("❌ Не удалось запустить бота")
        return
    
    print("\n🎉 Готово! Бот успешно запущен")

if __name__ == "__main__":
    main()