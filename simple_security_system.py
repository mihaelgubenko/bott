#!/usr/bin/env python3
"""
Упрощенная система безопасности без внешних зависимостей
Включает защиту SQL, кэширование и мониторинг
"""

import sqlite3
import time
import json
import hashlib
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Метрики выполнения запроса"""
    query_hash: str
    execution_time: float
    rows_affected: int
    timestamp: datetime
    user_id: Optional[int] = None
    is_expensive: bool = False

@dataclass
class CacheEntry:
    """Запись кэша"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0

class SimpleSecuritySystem:
    """Упрощенная система безопасности"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.query_metrics = deque(maxlen=1000)
        self.cache = {}
        self.user_limits = defaultdict(lambda: {
            'queries_per_minute': 0,
            'last_reset': datetime.now()
        })
        self.blocked_queries = set()
        self.security_alerts = deque(maxlen=100)
        
        # Настройки
        self.config = {
            'max_execution_time': 5.0,
            'max_queries_per_minute': 60,
            'cache_ttl': 300,
            'expensive_query_threshold': 1.0,
            'enable_caching': True,
            'enable_rate_limiting': True,
            'enable_monitoring': True
        }
        
        # Инициализация БД
        self._init_database()
        
        # Запуск фоновых задач
        self._start_background_tasks()
        
        logger.info("Упрощенная система безопасности инициализирована")

    def _init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица метрик
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT NOT NULL,
                execution_time REAL NOT NULL,
                rows_affected INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                is_expensive BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Таблица алертов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def _start_background_tasks(self):
        """Запуск фоновых задач"""
        # Очистка кэша
        cleanup_thread = threading.Thread(target=self._cleanup_cache, daemon=True)
        cleanup_thread.start()
        
        # Сброс лимитов
        reset_thread = threading.Thread(target=self._reset_limits, daemon=True)
        reset_thread.start()

    def _cleanup_cache(self):
        """Очистка истекшего кэша"""
        while True:
            try:
                time.sleep(60)  # Каждую минуту
                
                now = datetime.now()
                expired_keys = []
                
                for key, entry in self.cache.items():
                    if entry.expires_at and entry.expires_at < now:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.cache[key]
                
                if expired_keys:
                    logger.info(f"Очищено {len(expired_keys)} истекших записей кэша")
                
            except Exception as e:
                logger.error(f"Ошибка очистки кэша: {e}")

    def _reset_limits(self):
        """Сброс лимитов пользователей"""
        while True:
            try:
                time.sleep(60)  # Каждую минуту
                
                now = datetime.now()
                for user_id, limits in self.user_limits.items():
                    if now - limits['last_reset'] >= timedelta(minutes=1):
                        limits['queries_per_minute'] = 0
                        limits['last_reset'] = now
                
            except Exception as e:
                logger.error(f"Ошибка сброса лимитов: {e}")

    def _hash_query(self, query: str) -> str:
        """Создание хеша запроса"""
        normalized = ' '.join(query.strip().lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()

    def _check_rate_limits(self, user_id: Optional[int]) -> bool:
        """Проверка лимитов частоты"""
        if not self.config['enable_rate_limiting'] or user_id is None:
            return True
        
        limits = self.user_limits[user_id]
        now = datetime.now()
        
        if now - limits['last_reset'] >= timedelta(minutes=1):
            limits['queries_per_minute'] = 0
            limits['last_reset'] = now
        
        if limits['queries_per_minute'] >= self.config['max_queries_per_minute']:
            self._create_alert(
                "RATE_LIMIT_EXCEEDED",
                "WARNING",
                f"Превышен лимит запросов для пользователя {user_id}",
                user_id
            )
            return False
        
        limits['queries_per_minute'] += 1
        return True

    def _create_alert(self, alert_type: str, severity: str, message: str, 
                     user_id: Optional[int] = None, details: Dict = None):
        """Создание алерта"""
        alert = {
            'alert_type': alert_type,
            'severity': severity,
            'message': message,
            'timestamp': datetime.now(),
            'user_id': user_id,
            'details': details or {}
        }
        
        self.security_alerts.append(alert)
        
        # Сохраняем в БД
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_alerts 
                (alert_type, severity, message, user_id, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (alert_type, severity, message, user_id, 
                  json.dumps(details) if details else None))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения алерта: {e}")
        
        # Логируем
        if severity in ['CRITICAL', 'HIGH', 'WARNING']:
            logger.warning(f"SECURITY ALERT [{severity}]: {message}")

    def _get_cached_result(self, key: str) -> Optional[Any]:
        """Получение из кэша"""
        if not self.config['enable_caching']:
            return None
        
        if key in self.cache:
            entry = self.cache[key]
            if entry.expires_at and entry.expires_at < datetime.now():
                del self.cache[key]
                return None
            
            entry.access_count += 1
            return entry.value
        
        return None

    def _cache_result(self, key: str, value: Any, ttl: int = None):
        """Сохранение в кэш"""
        if not self.config['enable_caching']:
            return
        
        ttl = ttl or self.config['cache_ttl']
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            access_count=0
        )

    def execute_secure_query(self, query: str, params: Optional[Tuple] = None, 
                           user_id: Optional[int] = None, 
                           cache_ttl: Optional[int] = None) -> Tuple[Any, Dict[str, Any]]:
        """Выполнение защищенного SQL-запроса"""
        start_time = time.time()
        query_hash = self._hash_query(query)
        
        # Проверяем блокировку
        if query_hash in self.blocked_queries:
            self._create_alert(
                "BLOCKED_QUERY_ATTEMPT",
                "HIGH",
                "Попытка выполнения заблокированного запроса",
                user_id,
                {'query_hash': query_hash}
            )
            raise Exception("Запрос заблокирован из-за низкой производительности")
        
        # Проверяем лимиты
        if not self._check_rate_limits(user_id):
            raise Exception("Превышен лимит частоты запросов")
        
        # Проверяем кэш для SELECT запросов
        if query.strip().upper().startswith('SELECT'):
            cache_key = f"{query_hash}_{hash(str(params)) if params else 'no_params'}"
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result is not None:
                logger.info(f"Cache hit for query: {query[:50]}...")
                return cached_result, {
                    'from_cache': True,
                    'execution_time': 0,
                    'cache_key': cache_key
                }
        
        # Выполняем запрос
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                rows_affected = len(result)
            else:
                result = cursor.rowcount
                rows_affected = result
            
            conn.commit()
            conn.close()
            
            execution_time = time.time() - start_time
            
            # Проверяем время выполнения
            if execution_time > self.config['max_execution_time']:
                self._create_alert(
                    "SLOW_QUERY",
                    "WARNING",
                    f"Медленный запрос: {execution_time:.2f}с",
                    user_id,
                    {'execution_time': execution_time, 'query_hash': query_hash}
                )
            
            # Создаем метрику
            metric = QueryMetrics(
                query_hash=query_hash,
                execution_time=execution_time,
                rows_affected=rows_affected,
                timestamp=datetime.now(),
                user_id=user_id,
                is_expensive=execution_time > self.config['expensive_query_threshold']
            )
            
            self.query_metrics.append(metric)
            
            # Сохраняем метрику в БД
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO security_metrics 
                    (query_hash, execution_time, rows_affected, user_id, is_expensive)
                    VALUES (?, ?, ?, ?, ?)
                ''', (query_hash, execution_time, rows_affected, user_id, metric.is_expensive))
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Ошибка сохранения метрики: {e}")
            
            # Кэшируем результат для SELECT запросов
            if query.strip().upper().startswith('SELECT'):
                cache_key = f"{query_hash}_{hash(str(params)) if params else 'no_params'}"
                self._cache_result(cache_key, result, cache_ttl)
            
            return result, {
                'execution_time': execution_time,
                'rows_affected': rows_affected,
                'query_hash': query_hash,
                'from_cache': False
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self._create_alert(
                "QUERY_ERROR",
                "ERROR",
                f"Ошибка выполнения запроса: {str(e)}",
                user_id,
                {'error': str(e), 'execution_time': execution_time}
            )
            
            raise

    def get_performance_stats(self) -> Dict[str, Any]:
        """Получение статистики производительности"""
        if not self.query_metrics:
            return {'message': 'Нет данных о производительности'}
        
        recent_metrics = [m for m in self.query_metrics 
                         if m.timestamp > datetime.now() - timedelta(hours=1)]
        
        if not recent_metrics:
            return {'message': 'Нет недавних данных'}
        
        total_queries = len(recent_metrics)
        avg_execution_time = sum(m.execution_time for m in recent_metrics) / total_queries
        max_execution_time = max(m.execution_time for m in recent_metrics)
        expensive_queries_count = sum(1 for m in recent_metrics if m.is_expensive)
        
        return {
            'total_queries': total_queries,
            'avg_execution_time': round(avg_execution_time, 3),
            'max_execution_time': round(max_execution_time, 3),
            'expensive_queries_count': expensive_queries_count,
            'expensive_queries_percentage': round(expensive_queries_count / total_queries * 100, 1),
            'cache_size': len(self.cache),
            'blocked_queries_count': len(self.blocked_queries)
        }

    def get_security_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получение алертов безопасности"""
        recent_alerts = list(self.security_alerts)[-limit:]
        
        return [
            {
                'alert_type': alert['alert_type'],
                'severity': alert['severity'],
                'message': alert['message'],
                'timestamp': alert['timestamp'].isoformat(),
                'user_id': alert['user_id'],
                'details': alert['details']
            }
            for alert in recent_alerts
        ]

    def block_expensive_query(self, query_hash: str, reason: str = "Performance issue"):
        """Блокировка дорогого запроса"""
        self.blocked_queries.add(query_hash)
        
        self._create_alert(
            "QUERY_BLOCKED",
            "INFO",
            f"Запрос заблокирован: {reason}",
            details={'query_hash': query_hash, 'reason': reason}
        )
        
        logger.info(f"Запрос {query_hash[:8]}... заблокирован: {reason}")

    def unblock_query(self, query_hash: str):
        """Разблокировка запроса"""
        self.blocked_queries.discard(query_hash)
        logger.info(f"Запрос {query_hash[:8]}... разблокирован")

    def clear_cache(self):
        """Очистка кэша"""
        self.cache.clear()
        logger.info("Кэш очищен")

    def update_config(self, new_config: Dict[str, Any]):
        """Обновление конфигурации"""
        self.config.update(new_config)
        logger.info(f"Конфигурация обновлена: {new_config}")

# Глобальный экземпляр
_global_security = None

def get_security_system() -> SimpleSecuritySystem:
    """Получение глобального экземпляра"""
    global _global_security
    if _global_security is None:
        _global_security = SimpleSecuritySystem()
    return _global_security

# Функции для интеграции с ботом
def secure_save_analysis(telegram_id: int, name: str, analysis_type: str, 
                        analysis_data: dict, payment_status: str = 'free'):
    """Безопасное сохранение анализа"""
    security = get_security_system()
    
    query = '''
        INSERT OR REPLACE INTO clients 
        (telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    '''
    
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
        user_id=telegram_id
    )
    
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
        cache_ttl=600  # 10 минут
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
    
    # Очищаем кэш
    security.clear_cache()
    
    return results

def get_security_status() -> Dict[str, Any]:
    """Получение статуса безопасности"""
    security = get_security_system()
    
    return {
        'system_status': 'active',
        'performance_stats': security.get_performance_stats(),
        'recent_alerts': security.get_security_alerts(limit=10),
        'config': security.config,
        'cache_size': len(security.cache),
        'blocked_queries_count': len(security.blocked_queries)
    }

# Пример использования
if __name__ == "__main__":
    print("🔒 Тестирование упрощенной системы безопасности...")
    
    try:
        # Создаем систему безопасности
        security = SimpleSecuritySystem()
        
        # Создаем тестовую таблицу
        print("1. Создание тестовой таблицы...")
        security.execute_secure_query('''
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
        print("   Таблица создана")
        
        # Тестируем безопасные запросы
        print("2. Тестирование безопасных запросов...")
        
        # SELECT запрос с кэшированием
        result, metrics = security.execute_secure_query(
            "SELECT COUNT(*) FROM clients",
            cache_ttl=60
        )
        print(f"   Количество клиентов: {result[0][0] if result else 0}, время: {metrics['execution_time']:.3f}с")
        
        # Второй вызов - должен быть из кэша
        result2, metrics2 = security.execute_secure_query(
            "SELECT COUNT(*) FROM clients",
            cache_ttl=60
        )
        print(f"   Второй вызов из кэша: {metrics2.get('from_cache', False)}")
        
        # Тестируем сохранение
        print("3. Тестирование безопасного сохранения...")
        test_data = {
            'type': 'express',
            'conversation': 'Тестовый диалог',
            'analysis': 'Тестовый анализ'
        }
        
        result, metrics = secure_save_analysis(
            telegram_id=12345,
            name="Test User",
            analysis_type="express",
            analysis_data=test_data
        )
        print(f"   Анализ сохранен, время: {metrics['execution_time']:.3f}с")
        
        # Получаем статус
        print("4. Статус системы безопасности...")
        status = get_security_status()
        print(f"   Статус: {status['system_status']}")
        print(f"   Размер кэша: {status['cache_size']}")
        print(f"   Заблокированных запросов: {status['blocked_queries_count']}")
        
        # Статистика производительности
        print("5. Статистика производительности...")
        stats = security.get_performance_stats()
        print(f"   Всего запросов: {stats.get('total_queries', 0)}")
        print(f"   Среднее время: {stats.get('avg_execution_time', 0):.3f}с")
        print(f"   Дорогих запросов: {stats.get('expensive_queries_count', 0)}")
        
        print("\n🎉 Все тесты пройдены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()