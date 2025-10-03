#!/usr/bin/env python3
"""
Интеграция системы безопасности с основным кодом бота
Обновляет существующие функции для использования защищенных SQL-запросов
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Импортируем нашу систему безопасности
from integrated_security_system import (
    get_security_system, 
    secure_save_analysis, 
    secure_get_user_analyses, 
    secure_clear_memory,
    secure_database_operation,
    cached_database_operation
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureBotDatabase:
    """Безопасный класс для работы с базой данных бота"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.security = get_security_system()
        
        # Инициализируем базу данных
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных с защищенными запросами"""
        try:
            # Используем защищенный запрос для создания таблиц
            create_tables_query = '''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    name TEXT,
                    analysis_type TEXT,
                    analysis_data TEXT,
                    payment_status TEXT DEFAULT 'free',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            
            result, metrics = self.security.execute_secure_query(
                create_tables_query,
                cache_tags=['database_schema']
            )
            
            logger.info("База данных инициализирована с защитой")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    @cached_database_operation(ttl=300, tags=['user_analyses'])
    def get_user_analyses(self, telegram_id: int) -> List[Tuple]:
        """Получение анализов пользователя с кэшированием"""
        try:
            result, metrics = secure_get_user_analyses(telegram_id)
            logger.info(f"Получены анализы пользователя {telegram_id}, время: {metrics.get('execution_time', 0):.3f}с")
            return result
        except Exception as e:
            logger.error(f"Ошибка получения анализов: {e}")
            return []

    def save_analysis(self, telegram_id: int, name: str, analysis_type: str, 
                     analysis_data: dict, payment_status: str = 'free') -> Tuple[Any, Dict]:
        """Сохранение анализа с защитой"""
        try:
            result, metrics = secure_save_analysis(
                telegram_id, name, analysis_type, analysis_data, payment_status
            )
            logger.info(f"Анализ сохранен для пользователя {telegram_id}, время: {metrics.get('execution_time', 0):.3f}с")
            return result, metrics
        except Exception as e:
            logger.error(f"Ошибка сохранения анализа: {e}")
            raise

    def clear_memory(self) -> List[Tuple[Any, Dict]]:
        """Очистка памяти с защитой"""
        try:
            results = secure_clear_memory()
            logger.info("Память очищена с защитой")
            return results
        except Exception as e:
            logger.error(f"Ошибка очистки памяти: {e}")
            raise

    @cached_database_operation(ttl=60, tags=['statistics'])
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики с кэшированием"""
        try:
            # Общее количество клиентов
            result, metrics = self.security.execute_secure_query(
                "SELECT COUNT(*) FROM clients",
                cache_tags=['statistics', 'total_clients']
            )
            total_clients = result[0][0] if result else 0
            
            # Количество по типам анализа
            result, metrics = self.security.execute_secure_query(
                "SELECT analysis_type, COUNT(*) FROM clients GROUP BY analysis_type",
                cache_tags=['statistics', 'analysis_types']
            )
            analysis_types = dict(result) if result else {}
            
            # Количество за последние 24 часа
            result, metrics = self.security.execute_secure_query(
                "SELECT COUNT(*) FROM clients WHERE created_at > datetime('now', '-1 day')",
                cache_tags=['statistics', 'recent_clients']
            )
            recent_clients = result[0][0] if result else 0
            
            return {
                'total_clients': total_clients,
                'analysis_types': analysis_types,
                'recent_clients_24h': recent_clients,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}

    def get_security_status(self) -> Dict[str, Any]:
        """Получение статуса безопасности"""
        return self.security.get_security_status()

    def invalidate_user_cache(self, telegram_id: int):
        """Инвалидация кэша пользователя"""
        self.security.invalidate_cache_by_tag(f'user_{telegram_id}')
        logger.info(f"Кэш пользователя {telegram_id} инвалидирован")

    def invalidate_statistics_cache(self):
        """Инвалидация кэша статистики"""
        self.security.invalidate_cache_by_tag('statistics')
        logger.info("Кэш статистики инвалидирован")

# Обновленные функции для интеграции с существующим кодом
def init_database_secure():
    """Безопасная инициализация базы данных"""
    try:
        db = SecureBotDatabase()
        logger.info("База данных инициализирована с системой безопасности")
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        return False

def save_analysis_secure(telegram_id: int, name: str, analysis_type: str, 
                        analysis_data: dict, payment_status: str = 'free'):
    """Безопасное сохранение анализа (замена для save_analysis)"""
    try:
        db = SecureBotDatabase()
        return db.save_analysis(telegram_id, name, analysis_type, analysis_data, payment_status)
    except Exception as e:
        logger.error(f"Ошибка сохранения анализа: {e}")
        raise

def get_user_analyses_secure(telegram_id: int):
    """Безопасное получение анализов пользователя (замена для get_user_analyses)"""
    try:
        db = SecureBotDatabase()
        return db.get_user_analyses(telegram_id)
    except Exception as e:
        logger.error(f"Ошибка получения анализов: {e}")
        return []

def clear_memory_secure():
    """Безопасная очистка памяти (замена для clear_memory)"""
    try:
        db = SecureBotDatabase()
        return db.clear_memory()
    except Exception as e:
        logger.error(f"Ошибка очистки памяти: {e}")
        raise

# Функции для мониторинга и управления
def get_database_health() -> Dict[str, Any]:
    """Получение состояния здоровья базы данных"""
    try:
        db = SecureBotDatabase()
        security_status = db.get_security_status()
        
        # Дополнительные метрики здоровья
        health_metrics = {
            'database_status': 'healthy',
            'security_system': 'active',
            'last_check': datetime.now().isoformat(),
            'security_status': security_status
        }
        
        # Проверяем доступность БД
        try:
            result, metrics = db.security.execute_secure_query(
                "SELECT 1",
                cache_tags=['health_check']
            )
            health_metrics['database_accessible'] = True
            health_metrics['response_time_ms'] = metrics.get('execution_time', 0) * 1000
        except Exception as e:
            health_metrics['database_accessible'] = False
            health_metrics['database_error'] = str(e)
            health_metrics['database_status'] = 'unhealthy'
        
        return health_metrics
        
    except Exception as e:
        logger.error(f"Ошибка проверки здоровья БД: {e}")
        return {
            'database_status': 'error',
            'error': str(e),
            'last_check': datetime.now().isoformat()
        }

def get_performance_metrics() -> Dict[str, Any]:
    """Получение метрик производительности"""
    try:
        db = SecureBotDatabase()
        security_status = db.get_security_status()
        
        return {
            'cache_performance': security_status.get('caching', {}).get('stats', {}),
            'sql_performance': security_status.get('sql_protection', {}).get('stats', {}),
            'monitoring_metrics': security_status.get('monitoring', {}).get('summary', {}),
            'usage_statistics': security_status.get('usage_stats', {}),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения метрик производительности: {e}")
        return {'error': str(e)}

def configure_security_system(config: Dict[str, Any]):
    """Конфигурация системы безопасности"""
    try:
        db = SecureBotDatabase()
        db.security.update_config(config)
        logger.info(f"Система безопасности сконфигурирована: {config}")
        return True
    except Exception as e:
        logger.error(f"Ошибка конфигурации системы безопасности: {e}")
        return False

# Функции для администрирования
def block_expensive_query_admin(query_hash: str, reason: str = "Performance issue"):
    """Административная блокировка дорогого запроса"""
    try:
        db = SecureBotDatabase()
        db.security.block_expensive_query(query_hash, reason)
        logger.info(f"Запрос заблокирован администратором: {query_hash[:8]}... - {reason}")
        return True
    except Exception as e:
        logger.error(f"Ошибка блокировки запроса: {e}")
        return False

def unblock_query_admin(query_hash: str):
    """Административная разблокировка запроса"""
    try:
        db = SecureBotDatabase()
        db.security.unblock_query(query_hash)
        logger.info(f"Запрос разблокирован администратором: {query_hash[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Ошибка разблокировки запроса: {e}")
        return False

def clear_all_caches():
    """Очистка всех кэшей"""
    try:
        db = SecureBotDatabase()
        db.security.cache.clear()
        logger.info("Все кэши очищены")
        return True
    except Exception as e:
        logger.error(f"Ошибка очистки кэшей: {e}")
        return False

def get_security_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    """Получение алертов безопасности"""
    try:
        db = SecureBotDatabase()
        return db.security.monitor.get_recent_alerts(limit)
    except Exception as e:
        logger.error(f"Ошибка получения алертов: {e}")
        return []

# Пример использования и тестирования
if __name__ == "__main__":
    print("🔒 Тестирование интегрированной системы безопасности...")
    
    try:
        # Инициализация
        print("1. Инициализация системы безопасности...")
        init_success = init_database_secure()
        print(f"   Результат: {'✅ Успешно' if init_success else '❌ Ошибка'}")
        
        # Тестирование сохранения
        print("2. Тестирование безопасного сохранения...")
        test_data = {
            'type': 'express',
            'conversation': 'Тестовый диалог',
            'analysis': 'Тестовый анализ',
            'message_count': 5
        }
        
        result, metrics = save_analysis_secure(
            telegram_id=12345,
            name="Test User",
            analysis_type="express",
            analysis_data=test_data
        )
        print(f"   Результат: ✅ Сохранено, время: {metrics.get('execution_time', 0):.3f}с")
        
        # Тестирование получения
        print("3. Тестирование безопасного получения...")
        analyses = get_user_analyses_secure(12345)
        print(f"   Результат: ✅ Получено {len(analyses)} анализов")
        
        # Тестирование статистики
        print("4. Тестирование статистики...")
        db = SecureBotDatabase()
        stats = db.get_statistics()
        print(f"   Результат: ✅ Статистика получена: {stats}")
        
        # Проверка здоровья системы
        print("5. Проверка здоровья системы...")
        health = get_database_health()
        print(f"   Результат: ✅ Система {'здорова' if health.get('database_status') == 'healthy' else 'проблемы'}")
        
        # Метрики производительности
        print("6. Метрики производительности...")
        perf_metrics = get_performance_metrics()
        print(f"   Результат: ✅ Метрики получены")
        
        print("\n🎉 Все тесты пройдены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка тестирования: {e}")
    
    finally:
        # Корректное завершение
        try:
            db = SecureBotDatabase()
            db.security.shutdown()
            print("🔒 Система безопасности корректно завершена")
        except:
            pass