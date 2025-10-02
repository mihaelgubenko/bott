#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования системы синхронизации
HR-Психоаналитического бота
"""

import os
import json
import sqlite3
from datetime import datetime
from data_sync import get_sync_manager
from cloud_sync import get_cloud_sync_manager

def create_sample_data():
    """Создание тестовых данных для демонстрации"""
    print("🔧 Создание тестовых данных...")
    
    # Инициализируем базу данных
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    
    # Создаем таблицы если их нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            analysis_type TEXT,
            analysis_data TEXT,
            payment_status TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ab_test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt_variant_id TEXT NOT NULL,
            prompt_type TEXT NOT NULL,
            user_feedback REAL,
            response_quality REAL,
            user_engagement REAL,
            conversion BOOLEAN DEFAULT FALSE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_variant_assignments (
            user_id INTEGER,
            prompt_type TEXT,
            variant_id TEXT,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, prompt_type)
        )
    ''')
    
    # Добавляем тестовые данные
    sample_analyses = [
        (123456789, "Анна", "express", '{"type": "express", "analysis": "Тестовый экспресс-анализ"}', "free"),
        (987654321, "Петр", "full", '{"type": "full", "analysis": "Тестовый полный анализ"}', "paid"),
        (555666777, "Мария", "express", '{"type": "express", "analysis": "Еще один экспресс-анализ"}', "free"),
    ]
    
    for analysis in sample_analyses:
        cursor.execute('''
            INSERT OR REPLACE INTO clients 
            (telegram_id, name, analysis_type, analysis_data, payment_status)
            VALUES (?, ?, ?, ?, ?)
        ''', analysis)
    
    # Добавляем тестовые A/B результаты
    sample_ab_results = [
        (123456789, "express_analysis_a", "express_analysis", 4.5, 0.8, 0.7, True),
        (987654321, "psychology_consultation_b", "psychology_consultation", 4.0, 0.9, 0.8, False),
        (555666777, "express_analysis_b", "express_analysis", 4.8, 0.85, 0.75, True),
    ]
    
    for result in sample_ab_results:
        cursor.execute('''
            INSERT INTO ab_test_results 
            (user_id, prompt_variant_id, prompt_type, user_feedback, response_quality, user_engagement, conversion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', result)
    
    # Добавляем назначения вариантов
    sample_assignments = [
        (123456789, "express_analysis", "express_analysis_a"),
        (987654321, "psychology_consultation", "psychology_consultation_b"),
        (555666777, "express_analysis", "express_analysis_b"),
    ]
    
    for assignment in sample_assignments:
        cursor.execute('''
            INSERT OR REPLACE INTO user_variant_assignments 
            (user_id, prompt_type, variant_id)
            VALUES (?, ?, ?)
        ''', assignment)
    
    conn.commit()
    conn.close()
    
    print("✅ Тестовые данные созданы!")

def demo_export():
    """Демонстрация экспорта данных"""
    print("\n📤 Демонстрация экспорта данных...")
    
    sync_manager = get_sync_manager()
    
    # Экспорт в JSON
    print("Экспорт в JSON формат...")
    json_file = sync_manager.export_all_data('json')
    print(f"✅ JSON экспорт: {json_file}")
    
    # Экспорт в CSV
    print("Экспорт в CSV формат...")
    csv_file = sync_manager.export_all_data('csv')
    print(f"✅ CSV экспорт: {csv_file}")
    
    # Информация об экспортах
    export_info = sync_manager.get_export_info()
    print(f"\n📊 Информация об экспортах:")
    print(f"  - Папка: {export_info['export_dir']}")
    print(f"  - Количество экспортов: {export_info['total_exports']}")
    
    for export in export_info['available_exports']:
        print(f"  - {export['filename']}: {export['total_analyses']} анализов, {export['file_size']} байт")

def demo_import():
    """Демонстрация импорта данных"""
    print("\n📥 Демонстрация импорта данных...")
    
    sync_manager = get_sync_manager()
    
    # Получаем последний экспорт
    export_info = sync_manager.get_export_info()
    if not export_info['available_exports']:
        print("❌ Нет файлов для импорта")
        return
    
    # Берем последний JSON экспорт
    json_exports = [e for e in export_info['available_exports'] if e['filename'].endswith('.json')]
    if not json_exports:
        print("❌ Нет JSON файлов для импорта")
        return
    
    latest_export = json_exports[0]
    file_path = latest_export['filepath']
    
    print(f"Импорт из файла: {latest_export['filename']}")
    
    try:
        result = sync_manager.import_data(file_path, merge_mode=True)
        print(f"✅ Импорт завершен:")
        print(f"  - Анализов: {result['analyses']}")
        print(f"  - A/B результатов: {result['ab_results']}")
        print(f"  - Назначений: {result['assignments']}")
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")

def demo_cloud_sync():
    """Демонстрация облачной синхронизации"""
    print("\n☁️ Демонстрация облачной синхронизации...")
    
    cloud_sync = get_cloud_sync_manager()
    
    # Показываем текущий статус
    status = cloud_sync.get_sync_status()
    print(f"📊 Статус синхронизации:")
    print(f"  - Включена: {status['enabled']}")
    print(f"  - Последняя синхронизация: {status['last_sync']}")
    print(f"  - Следующая синхронизация: {status['next_sync']}")
    
    # Настройка сервисов (заглушки)
    print("\n🔧 Настройка сервисов...")
    print("  - Google Drive: настройка (заглушка)")
    print("  - Dropbox: настройка (заглушка)")
    
    # Включение автоматической синхронизации
    cloud_sync.enable_auto_sync(24)
    print("✅ Автоматическая синхронизация включена (каждые 24 часа)")
    
    # Ручная синхронизация
    print("\n🔄 Ручная синхронизация...")
    result = cloud_sync.manual_sync()
    print(f"Результат: {result['status']}")
    
    if result['status'] == 'success':
        print(f"  - Файл экспорта: {result['export_file']}")
        print(f"  - Время синхронизации: {result['sync_time']}")
        
        for service, service_result in result['services'].items():
            print(f"  - {service}: {service_result['status']}")

def demo_web_interface():
    """Демонстрация веб-интерфейса"""
    print("\n🌐 Демонстрация веб-интерфейса...")
    
    print("📋 Возможности веб-интерфейса:")
    print("  - 📊 Панель управления с статистикой")
    print("  - 📋 Просмотр всех анализов")
    print("  - 👁️ Детальный просмотр анализов")
    print("  - 📤 Экспорт данных в разных форматах")
    print("  - 📥 Импорт данных через браузер")
    print("  - 📈 Детальная статистика и аналитика")
    
    print("\n🚀 Для запуска веб-интерфейса:")
    print("  python web_interface.py")
    print("  Откройте: http://localhost:5000")

def demo_telegram_commands():
    """Демонстрация Telegram команд"""
    print("\n🤖 Демонстрация Telegram команд...")
    
    print("📋 Команды для синхронизации:")
    print("  /export [json|csv] - экспорт данных")
    print("  /import - импорт данных (отправить файл)")
    print("  /sync - информация о синхронизации")
    print("  /stats - статистика A/B тестов")
    print("  /clear - очистка памяти бота")
    
    print("\n💡 Примеры использования:")
    print("  /export json")
    print("  /export csv")
    print("  /import (затем отправить файл)")
    print("  /sync")

def show_database_stats():
    """Показать статистику базы данных"""
    print("\n📊 Статистика базы данных:")
    
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    
    # Подсчет анализов
    cursor.execute('SELECT COUNT(*) FROM clients')
    total_analyses = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM clients WHERE analysis_type = "express"')
    express_analyses = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM clients WHERE analysis_type = "full"')
    full_analyses = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM clients WHERE payment_status = "paid"')
    paid_analyses = cursor.fetchone()[0]
    
    # Подсчет A/B тестов
    cursor.execute('SELECT COUNT(*) FROM ab_test_results')
    total_ab_tests = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"  - Всего анализов: {total_analyses}")
    print(f"  - Экспресс-анализы: {express_analyses}")
    print(f"  - Полные анализы: {full_analyses}")
    print(f"  - Платные анализы: {paid_analyses}")
    print(f"  - A/B тестов: {total_ab_tests}")

def main():
    """Главная функция демонстрации"""
    print("🔄 Демонстрация системы синхронизации HR-Психоаналитика")
    print("=" * 60)
    
    # Создаем тестовые данные
    create_sample_data()
    
    # Показываем статистику
    show_database_stats()
    
    # Демонстрируем экспорт
    demo_export()
    
    # Демонстрируем импорт
    demo_import()
    
    # Демонстрируем облачную синхронизацию
    demo_cloud_sync()
    
    # Демонстрируем веб-интерфейс
    demo_web_interface()
    
    # Демонстрируем Telegram команды
    demo_telegram_commands()
    
    print("\n" + "=" * 60)
    print("✅ Демонстрация завершена!")
    print("\n💡 Следующие шаги:")
    print("  1. Запустите бота: python hr_psychoanalyst_bot.py")
    print("  2. Запустите веб-интерфейс: python web_interface.py")
    print("  3. Протестируйте команды /export и /import")
    print("  4. Прочитайте SYNC_GUIDE.md для подробной документации")

if __name__ == "__main__":
    main()