#!/usr/bin/env python3
"""
Скрипт для очистки памяти бота
Использование: python clear_memory.py
"""

import os
import sqlite3
import glob

def clear_bot_memory():
    """Очистить всю память бота"""
    print("🧹 Очистка памяти бота...")
    
    # 1. Очистка базы данных
    db_files = ['psychoanalyst.db', 'clients.db', 'candidates.db']
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM clients')
                conn.commit()
                conn.close()
                print(f"✅ Очищена база данных: {db_file}")
            except Exception as e:
                print(f"❌ Ошибка при очистке {db_file}: {e}")
    
    # 2. Очистка кэша Python
    cache_dirs = ['__pycache__', '.pytest_cache']
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                import shutil
                shutil.rmtree(cache_dir)
                print(f"✅ Очищен кэш: {cache_dir}")
            except Exception as e:
                print(f"❌ Ошибка при очистке {cache_dir}: {e}")
    
    # 3. Очистка логов
    log_files = glob.glob('*.log')
    for log_file in log_files:
        try:
            os.remove(log_file)
            print(f"✅ Удален лог: {log_file}")
        except Exception as e:
            print(f"❌ Ошибка при удалении {log_file}: {e}")
    
    print("\n🎉 Память бота полностью очищена!")
    print("💡 При следующем деплое бот запустится с чистой памятью")

if __name__ == "__main__":
    clear_bot_memory()
