#!/usr/bin/env python3
"""
Скрипт для создания нового HR-психоаналитического бота
Позволяет быстро создать новую версию бота с настройками
"""

import os
import shutil
import json
from datetime import datetime

def create_new_bot():
    """Создание нового бота на основе существующего"""
    
    print("🤖 Создание нового HR-психоаналитического бота")
    print("=" * 50)
    
    # Получение параметров от пользователя
    bot_name = input("Введите имя бота (например: mobile_hr_bot): ").strip()
    if not bot_name:
        bot_name = f"hr_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    bot_description = input("Введите описание бота: ").strip()
    if not bot_description:
        bot_description = "HR-психоаналитический бот"
    
    # Создание директории для нового бота
    bot_dir = f"bots/{bot_name}"
    os.makedirs(bot_dir, exist_ok=True)
    
    print(f"\n📁 Создана директория: {bot_dir}")
    
    # Копирование основных файлов
    files_to_copy = [
        ("hr_psychoanalyst_bot.py", f"{bot_dir}/main.py"),
        ("sentiment_analyzer.py", f"{bot_dir}/sentiment_analyzer.py"),
        ("prompt_ab_testing.py", f"{bot_dir}/prompt_ab_testing.py"),
        ("requirements.txt", f"{bot_dir}/requirements.txt"),
        ("Procfile", f"{bot_dir}/Procfile"),
        ("railway.json", f"{bot_dir}/railway.json"),
    ]
    
    for source, destination in files_to_copy:
        if os.path.exists(source):
            shutil.copy2(source, destination)
            print(f"✅ Скопирован: {source} -> {destination}")
        else:
            print(f"⚠️  Файл не найден: {source}")
    
    # Создание конфигурационного файла
    config = {
        "bot_name": bot_name,
        "description": bot_description,
        "created_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "features": [
            "Психологическая поддержка",
            "Анализ личности",
            "Карьерное консультирование",
            "A/B тестирование",
            "Анализ эмоций"
        ],
        "database": f"{bot_name}.db",
        "port": 8000
    }
    
    config_file = f"{bot_dir}/bot_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Создан конфиг: {config_file}")
    
    # Создание .env файла-шаблона
    env_template = f"""{bot_dir}/.env.template
# Конфигурация для {bot_name}
# Скопируйте этот файл в .env и заполните значения

BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
PAYMENT_TOKEN=your_payment_token_here

# Дополнительные настройки
DEBUG=False
LOG_LEVEL=INFO
MAX_MESSAGE_LENGTH=4000
"""
    
    with open(f"{bot_dir}/.env.template", 'w', encoding='utf-8') as f:
        f.write(env_template)
    
    print(f"✅ Создан шаблон .env: {bot_dir}/.env.template")
    
    # Создание README для нового бота
    readme_content = f"""# {bot_description}

Автоматически создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Быстрый запуск

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Настройте переменные окружения:
   ```bash
   cp .env.template .env
   # Отредактируйте .env файл
   ```

3. Запустите бота:
   ```bash
   python main.py
   ```

## Особенности

- Психологическая поддержка
- Анализ личности
- Карьерное консультирование
- A/B тестирование промптов
- Анализ эмоций в реальном времени

## Конфигурация

Настройки бота находятся в файле `bot_config.json`
"""
    
    with open(f"{bot_dir}/README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ Создан README: {bot_dir}/README.md")
    
    # Создание скрипта запуска
    run_script = f"""#!/bin/bash
# Скрипт запуска для {bot_name}

echo "🤖 Запуск {bot_name}..."
echo "📁 Директория: $(pwd)"
echo "🐍 Python версия: $(python --version)"

# Проверка .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден!"
    echo "📋 Скопируйте .env.template в .env и заполните значения"
    exit 1
fi

# Проверка зависимостей
echo "📦 Проверка зависимостей..."
pip install -r requirements.txt

# Запуск бота
echo "🚀 Запуск бота..."
python main.py
"""
    
    with open(f"{bot_dir}/run.sh", 'w', encoding='utf-8') as f:
        f.write(run_script)
    
    # Делаем скрипт исполняемым
    os.chmod(f"{bot_dir}/run.sh", 0o755)
    
    print(f"✅ Создан скрипт запуска: {bot_dir}/run.sh")
    
    # Создание Dockerfile (опционально)
    dockerfile_content = f"""FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание пользователя
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Запуск бота
CMD ["python", "main.py"]
"""
    
    with open(f"{bot_dir}/Dockerfile", 'w', encoding='utf-8') as f:
        f.write(dockerfile_content)
    
    print(f"✅ Создан Dockerfile: {bot_dir}/Dockerfile")
    
    # Создание docker-compose.yml
    compose_content = f"""version: '3.8'

services:
  {bot_name}:
    build: .
    container_name: {bot_name}
    restart: unless-stopped
    environment:
      - BOT_TOKEN=${{BOT_TOKEN}}
      - OPENAI_API_KEY=${{OPENAI_API_KEY}}
      - PAYMENT_TOKEN=${{PAYMENT_TOKEN}}
    volumes:
      - ./data:/app/data
    env_file:
      - .env
"""
    
    with open(f"{bot_dir}/docker-compose.yml", 'w', encoding='utf-8') as f:
        f.write(compose_content)
    
    print(f"✅ Создан docker-compose.yml: {bot_dir}/docker-compose.yml")
    
    # Создание директории для данных
    os.makedirs(f"{bot_dir}/data", exist_ok=True)
    
    print(f"\n🎉 Бот '{bot_name}' успешно создан!")
    print("=" * 50)
    print(f"📁 Директория: {bot_dir}")
    print(f"📋 Конфигурация: {bot_dir}/bot_config.json")
    print(f"🔧 Шаблон .env: {bot_dir}/.env.template")
    print(f"📖 README: {bot_dir}/README.md")
    print(f"🚀 Скрипт запуска: {bot_dir}/run.sh")
    print(f"🐳 Docker: {bot_dir}/Dockerfile")
    
    print("\n📝 Следующие шаги:")
    print(f"1. cd {bot_dir}")
    print("2. cp .env.template .env")
    print("3. Отредактируйте .env файл")
    print("4. ./run.sh")
    
    return bot_dir

def list_created_bots():
    """Показать список созданных ботов"""
    bots_dir = "bots"
    if not os.path.exists(bots_dir):
        print("📁 Директория bots не найдена")
        return
    
    bots = os.listdir(bots_dir)
    if not bots:
        print("🤖 Созданных ботов не найдено")
        return
    
    print("🤖 Созданные боты:")
    print("=" * 30)
    
    for bot in bots:
        bot_path = os.path.join(bots_dir, bot)
        if os.path.isdir(bot_path):
            config_file = os.path.join(bot_path, "bot_config.json")
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    print(f"📱 {bot}")
                    print(f"   Описание: {config.get('description', 'Нет описания')}")
                    print(f"   Создан: {config.get('created_at', 'Неизвестно')}")
                    print(f"   Версия: {config.get('version', 'Неизвестно')}")
                except:
                    print(f"📱 {bot} (ошибка чтения конфига)")
            else:
                print(f"📱 {bot} (нет конфига)")

def main():
    """Главное меню"""
    while True:
        print("\n🤖 Генератор HR-психоаналитических ботов")
        print("=" * 40)
        print("1. Создать нового бота")
        print("2. Показать созданных ботов")
        print("3. Выход")
        
        choice = input("\nВыберите действие (1-3): ").strip()
        
        if choice == "1":
            create_new_bot()
        elif choice == "2":
            list_created_bots()
        elif choice == "3":
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()