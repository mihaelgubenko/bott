#!/usr/bin/env python3
"""
Интегрированная система безопасности для бота
Объединяет защиту SQL, кэширование, мониторинг и алертинг
"""

import sqlite3
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from functools import wraps

# Импортируем наши модули безопасности
from sql_protection_system import SQLProtectionSystem, protected_sql_query
from advanced_caching_system import MultiLevelCache, cached, cached_sql_query, get_cache
from database_monitoring_system import DatabaseMonitoringSystem, get_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedSecuritySystem:
    """Интегрированная система безопасности"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        
        # Инициализируем компоненты безопасности
        self.sql_protection = SQLProtectionSystem(db_path)
        self.cache = MultiLevelCache(db_path)
        self.monitor = DatabaseMonitoringSystem(db_path)
        
        # Настройки интеграции
        self.config = {
            'enable_sql_protection': True,
            'enable_caching': True,
            'enable_monitoring': True,
            'cache_ttl_default': 300,  # 5 минут
            'monitoring_interval': 60,  # 1 минута
            'auto_start_monitoring': True
        }
        
        # Статистика использования
        self.usage_stats = {
            'total_queries': 0,
            'cached_queries': 0,
            'blocked_queries': 0,
            'security_alerts': 0,
            'start_time': datetime.now()
        }
        
        # Запускаем мониторинг
        if self.config['auto_start_monitoring']:
            self.monitor.start_monitoring(self.config['monitoring_interval'])
        
        logger.info("Интегрированная система безопасности инициализирована")

    def execute_secure_query(self, query: str, params: Optional[Tuple] = None, 
                           user_id: Optional[int] = None, 
                           cache_ttl: Optional[int] = None,
                           cache_tags: List[str] = None) -> Tuple[Any, Dict[str, Any]]:
        """Выполнение защищенного SQL-запроса с полной интеграцией"""
        start_time = time.time()
        self.usage_stats['total_queries'] += 1
        
        try:
            # 1. Проверяем кэш (только для SELECT запросов)
            if (self.config['enable_caching'] and 
                query.strip().upper().startswith('SELECT')):
                
                cache_key = self._generate_cache_key(query, params, cache_tags)
                cached_result = self.cache.get(cache_key)
                
                if cached_result is not None:
                    self.usage_stats['cached_queries'] += 1
                    execution_time = time.time() - start_time
                    
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    
                    return cached_result, {
                        'from_cache': True,
                        'execution_time': execution_time,
                        'cache_key': cache_key,
                        'security_checks': 'passed'
                    }
            
            # 2. Выполняем защищенный запрос
            if self.config['enable_sql_protection']:
                result, metrics = self.sql_protection.execute_protected_query(
                    query, params, user_id
                )
            else:
                # Прямое выполнение без защиты (не рекомендуется)
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                metrics = {
                    'execution_time': time.time() - start_time,
                    'rows_affected': len(result) if isinstance(result, list) else result,
                    'from_cache': False
                }
            
            # 3. Кэшируем результат (только для SELECT запросов)
            if (self.config['enable_caching'] and 
                query.strip().upper().startswith('SELECT')):
                
                cache_key = self._generate_cache_key(query, params, cache_tags)
                ttl = cache_ttl or self.config['cache_ttl_default']
                self.cache.set(cache_key, result, ttl, cache_tags, ['sql_database'])
            
            # 4. Обновляем статистику
            execution_time = time.time() - start_time
            metrics.update({
                'total_execution_time': execution_time,
                'cache_key': cache_key if 'cache_key' in locals() else None,
                'security_checks': 'passed'
            })
            
            return result, metrics
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.usage_stats['security_alerts'] += 1
            
            logger.error(f"Ошибка выполнения защищенного запроса: {e}")
            
            # Создаем алерт о блокировке
            if "заблокирован" in str(e).lower() or "blocked" in str(e).lower():
                self.usage_stats['blocked_queries'] += 1
            
            raise

    def _generate_cache_key(self, query: str, params: Optional[Tuple] = None, 
                          tags: List[str] = None) -> str:
        """Генерация ключа кэша"""
        import hashlib
        import json
        
        key_data = {
            'query': query,
            'params': params,
            'tags': sorted(tags) if tags else []
        }
        
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_security_status(self) -> Dict[str, Any]:
        """Получение статуса безопасности"""
        # Статистика SQL защиты
        sql_stats = self.sql_protection.get_performance_stats()
        
        # Статистика кэша
        cache_stats = self.cache.get_stats()
        
        # Статистика мониторинга
        monitor_summary = self.monitor.get_metrics_summary(hours=1)
        
        # Статистика использования
        uptime = datetime.now() - self.usage_stats['start_time']
        
        return {
            'system_status': 'active',
            'uptime_seconds': int(uptime.total_seconds()),
            'usage_stats': {
                'total_queries': self.usage_stats['total_queries'],
                'cached_queries': self.usage_stats['cached_queries'],
                'blocked_queries': self.usage_stats['blocked_queries'],
                'security_alerts': self.usage_stats['security_alerts'],
                'cache_hit_rate': (
                    self.usage_stats['cached_queries'] / self.usage_stats['total_queries'] 
                    if self.usage_stats['total_queries'] > 0 else 0
                )
            },
            'sql_protection': {
                'enabled': self.config['enable_sql_protection'],
                'stats': sql_stats
            },
            'caching': {
                'enabled': self.config['enable_caching'],
                'stats': cache_stats
            },
            'monitoring': {
                'enabled': self.config['enable_monitoring'],
                'summary': monitor_summary
            },
            'recent_alerts': self.monitor.get_recent_alerts(limit=10)
        }

    def invalidate_cache_by_tag(self, tag: str):
        """Инвалидация кэша по тегу"""
        if self.config['enable_caching']:
            self.cache.invalidate_by_tag(tag)
            logger.info(f"Кэш инвалидирован по тегу: {tag}")

    def invalidate_cache_by_dependency(self, dependency: str):
        """Инвалидация кэша по зависимости"""
        if self.config['enable_caching']:
            self.cache.invalidate_by_dependency(dependency)
            logger.info(f"Кэш инвалидирован по зависимости: {dependency}")

    def block_expensive_query(self, query_hash: str, reason: str = "Performance issue"):
        """Заблокировать дорогой запрос"""
        if self.config['enable_sql_protection']:
            self.sql_protection.block_expensive_query(query_hash, reason)
            logger.info(f"Запрос заблокирован: {query_hash[:8]}... - {reason}")

    def unblock_query(self, query_hash: str):
        """Разблокировать запрос"""
        if self.config['enable_sql_protection']:
            self.sql_protection.unblock_query(query_hash)
            logger.info(f"Запрос разблокирован: {query_hash[:8]}...")

    def update_config(self, new_config: Dict[str, Any]):
        """Обновление конфигурации"""
        self.config.update(new_config)
        
        # Обновляем конфигурации компонентов
        if 'sql_protection_config' in new_config:
            self.sql_protection.update_config(new_config['sql_protection_config'])
        
        if 'monitoring_config' in new_config:
            self.monitor.update_alert_config(new_config['monitoring_config'])
        
        logger.info(f"Конфигурация обновлена: {new_config}")

    def shutdown(self):
        """Корректное завершение работы системы"""
        logger.info("Завершение работы системы безопасности...")
        
        if self.config['enable_monitoring']:
            self.monitor.stop_monitoring()
        
        # Очищаем кэш
        if self.config['enable_caching']:
            self.cache.clear()
        
        logger.info("Система безопасности завершена")

# Глобальный экземпляр системы безопасности
_global_security = None

def get_security_system() -> IntegratedSecuritySystem:
    """Получение глобального экземпляра системы безопасности"""
    global _global_security
    if _global_security is None:
        _global_security = IntegratedSecuritySystem()
    return _global_security

# Декораторы для интеграции с существующим кодом
def secure_database_operation(user_id: Optional[int] = None, 
                            cache_ttl: Optional[int] = None,
                            cache_tags: List[str] = None):
    """Декоратор для защиты операций с базой данных"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            security = get_security_system()
            
            # Если функция возвращает SQL-запрос, выполняем его безопасно
            if hasattr(func, '_returns_sql_query'):
                query = func(*args, **kwargs)
                if isinstance(query, str):
                    return security.execute_secure_query(
                        query, user_id=user_id, cache_ttl=cache_ttl, cache_tags=cache_tags
                    )
            
            # Иначе просто выполняем функцию
            return func(*args, **kwargs)
        
        wrapper._returns_sql_query = True
        return wrapper
    return decorator

def cached_database_operation(ttl: int = 300, tags: List[str] = None):
    """Декоратор для кэширования операций с базой данных"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Генерируем ключ кэша
            cache_key = cache._generate_key(func.__name__, args, kwargs, tags)
            
            # Пытаемся получить из кэша
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Выполняем функцию
            logger.debug(f"Cache miss for {func.__name__}, executing...")
            result = func(*args, **kwargs)
            
            # Сохраняем в кэш
            cache.set(cache_key, result, ttl, tags, ['database_operation'])
            
            return result
        
        return wrapper
    return decorator

# Функции для интеграции с существующим кодом бота
def secure_save_analysis(telegram_id: int, name: str, analysis_type: str, 
                        analysis_data: dict, payment_status: str = 'free'):
    """Безопасное сохранение анализа"""
    security = get_security_system()
    
    query = '''
        INSERT OR REPLACE INTO clients 
        (telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    '''
    
    import json
    from datetime import datetime
    
    params = (
        telegram_id, 
        name, 
        analysis_type, 
        json.dumps(analysis_data), 
        payment_status, 
        datetime.now()
    )
    
    result, metrics = security.execute_secure_query(
        query, 
        params, 
        user_id=telegram_id,
        cache_tags=['user_data', f'user_{telegram_id}']
    )
    
    # Инвалидируем кэш пользователя
    security.invalidate_cache_by_tag(f'user_{telegram_id}')
    
    return result, metrics

def secure_get_user_analyses(telegram_id: int):
    """Безопасное получение анализов пользователя"""
    security = get_security_system()
    
    query = 'SELECT * FROM clients WHERE telegram_id = ? ORDER BY created_at DESC'
    params = (telegram_id,)
    
    result, metrics = security.execute_secure_query(
        query, 
        params, 
        user_id=telegram_id,
        cache_ttl=600,  # 10 минут
        cache_tags=['user_data', f'user_{telegram_id}']
    )
    
    return result, metrics

def secure_clear_memory():
    """Безопасная очистка памяти"""
    security = get_security_system()
    
    queries = [
        'DELETE FROM clients',
        'DELETE FROM user_variant_assignments',
        'DELETE FROM ab_test_results'
    ]
    
    results = []
    for query in queries:
        result, metrics = security.execute_secure_query(query, user_id=None)
        results.append((result, metrics))
    
    # Очищаем весь кэш
    security.cache.clear()
    
    return results

# Пример использования
if __name__ == "__main__":
    # Создаем систему безопасности
    security = IntegratedSecuritySystem()
    
    try:
        # Тестируем безопасные запросы
        print("Тестирование безопасных запросов...")
        
        # SELECT запрос с кэшированием
        result, metrics = security.execute_secure_query(
            "SELECT COUNT(*) FROM clients",
            cache_ttl=60,
            cache_tags=['statistics']
        )
        print(f"Количество клиентов: {result[0][0]}, метрики: {metrics}")
        
        # Второй вызов - должен быть из кэша
        result2, metrics2 = security.execute_secure_query(
            "SELECT COUNT(*) FROM clients",
            cache_ttl=60,
            cache_tags=['statistics']
        )
        print(f"Второй вызов из кэша: {metrics2.get('from_cache', False)}")
        
        # Получаем статус безопасности
        status = security.get_security_status()
        print(f"Статус безопасности: {status['system_status']}")
        print(f"Статистика использования: {status['usage_stats']}")
        
        # Тестируем инвалидацию кэша
        security.invalidate_cache_by_tag('statistics')
        print("Кэш инвалидирован по тегу 'statistics'")
        
    finally:
        # Корректно завершаем работу
        security.shutdown()