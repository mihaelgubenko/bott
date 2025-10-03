#!/usr/bin/env python3
"""
Система защиты от дорогих SQL-запросов и оптимизации производительности
Включает мониторинг, ограничения, кэширование и защиту от атак
"""

import sqlite3
import time
import logging
import hashlib
import json
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import re
import functools

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
    query_type: str = "unknown"
    is_expensive: bool = False

@dataclass
class SecurityAlert:
    """Алерт безопасности"""
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    user_id: Optional[int] = None
    query_hash: Optional[str] = None
    details: Dict[str, Any] = None

class SQLProtectionSystem:
    """Система защиты SQL-запросов"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.query_metrics = deque(maxlen=10000)  # Храним последние 10k запросов
        self.user_limits = defaultdict(lambda: {
            'queries_per_minute': 0,
            'queries_per_hour': 0,
            'last_reset_minute': datetime.now(),
            'last_reset_hour': datetime.now()
        })
        self.expensive_queries = set()
        self.blocked_queries = set()
        self.query_cache = {}
        self.security_alerts = deque(maxlen=1000)
        
        # Настройки защиты
        self.config = {
            'max_execution_time': 5.0,  # Максимальное время выполнения (секунды)
            'max_queries_per_minute': 60,  # Максимум запросов в минуту на пользователя
            'max_queries_per_hour': 1000,  # Максимум запросов в час на пользователя
            'cache_ttl': 300,  # Время жизни кэша (секунды)
            'expensive_query_threshold': 1.0,  # Порог для дорогих запросов (секунды)
            'max_rows_per_query': 10000,  # Максимум строк в результате
            'enable_query_analysis': True,  # Включить анализ запросов
            'enable_rate_limiting': True,  # Включить ограничение частоты
            'enable_caching': True,  # Включить кэширование
            'enable_security_monitoring': True  # Включить мониторинг безопасности
        }
        
        # Паттерны опасных запросов
        self.dangerous_patterns = [
            r'SELECT\s+\*\s+FROM',  # SELECT * FROM
            r'DELETE\s+FROM\s+\w+\s*$',  # DELETE FROM table
            r'DROP\s+TABLE',  # DROP TABLE
            r'TRUNCATE\s+TABLE',  # TRUNCATE TABLE
            r'ALTER\s+TABLE',  # ALTER TABLE
            r'CREATE\s+TABLE',  # CREATE TABLE
            r'INSERT\s+INTO\s+\w+\s+SELECT',  # INSERT INTO ... SELECT
            r'UPDATE\s+\w+\s+SET.*WHERE\s*$',  # UPDATE без WHERE
            r'SELECT.*FROM.*WHERE\s*$',  # SELECT без WHERE
            r'SELECT.*COUNT\(\*\).*FROM',  # COUNT(*) без LIMIT
            r'SELECT.*FROM.*ORDER\s+BY.*LIMIT\s+\d{4,}',  # Большой LIMIT
        ]
        
        # Инициализация
        self._init_database()
        self._load_expensive_queries()
        
        # Запуск фоновых задач
        self._start_background_tasks()

    def _init_database(self):
        """Инициализация таблиц для мониторинга"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица метрик запросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT NOT NULL,
                execution_time REAL NOT NULL,
                rows_affected INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                query_type TEXT,
                is_expensive BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Таблица алертов безопасности
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                query_hash TEXT,
                details TEXT
            )
        ''')
        
        # Таблица дорогих запросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expensive_queries (
                query_hash TEXT PRIMARY KEY,
                avg_execution_time REAL NOT NULL,
                max_execution_time REAL NOT NULL,
                call_count INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_blocked BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Индексы для оптимизации
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_query_metrics_timestamp 
            ON query_metrics(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_query_metrics_user_id 
            ON query_metrics(user_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_security_alerts_timestamp 
            ON security_alerts(timestamp)
        ''')
        
        conn.commit()
        conn.close()

    def _load_expensive_queries(self):
        """Загрузка списка дорогих запросов из БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT query_hash, is_blocked 
                FROM expensive_queries 
                WHERE is_blocked = TRUE
            ''')
            
            for row in cursor.fetchall():
                self.blocked_queries.add(row[0])
            
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка загрузки дорогих запросов: {e}")

    def _start_background_tasks(self):
        """Запуск фоновых задач"""
        # Очистка старых метрик
        cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        cleanup_thread.start()
        
        # Анализ производительности
        analysis_thread = threading.Thread(target=self._analyze_performance, daemon=True)
        analysis_thread.start()
        
        # Сброс лимитов пользователей
        reset_thread = threading.Thread(target=self._reset_user_limits, daemon=True)
        reset_thread.start()

    def _cleanup_old_metrics(self):
        """Очистка старых метрик"""
        while True:
            try:
                time.sleep(3600)  # Каждый час
                
                cutoff_time = datetime.now() - timedelta(days=7)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM query_metrics 
                    WHERE timestamp < ?
                ''', (cutoff_time,))
                
                cursor.execute('''
                    DELETE FROM security_alerts 
                    WHERE timestamp < ?
                ''', (cutoff_time,))
                
                conn.commit()
                conn.close()
                
                logger.info("Очистка старых метрик завершена")
                
            except Exception as e:
                logger.error(f"Ошибка очистки метрик: {e}")

    def _analyze_performance(self):
        """Анализ производительности запросов"""
        while True:
            try:
                time.sleep(300)  # Каждые 5 минут
                
                # Анализируем последние метрики
                recent_metrics = [m for m in self.query_metrics 
                                if m.timestamp > datetime.now() - timedelta(minutes=5)]
                
                if not recent_metrics:
                    continue
                
                # Группируем по хешу запроса
                query_stats = defaultdict(list)
                for metric in recent_metrics:
                    query_stats[metric.query_hash].append(metric)
                
                # Находим дорогие запросы
                for query_hash, metrics in query_stats.items():
                    avg_time = sum(m.execution_time for m in metrics) / len(metrics)
                    max_time = max(m.execution_time for m in metrics)
                    
                    if avg_time > self.config['expensive_query_threshold']:
                        self._mark_expensive_query(query_hash, avg_time, max_time, len(metrics))
                
                logger.info(f"Анализ производительности: {len(query_stats)} уникальных запросов")
                
            except Exception as e:
                logger.error(f"Ошибка анализа производительности: {e}")

    def _reset_user_limits(self):
        """Сброс лимитов пользователей"""
        while True:
            try:
                time.sleep(60)  # Каждую минуту
                
                now = datetime.now()
                
                for user_id, limits in self.user_limits.items():
                    # Сброс минутных лимитов
                    if now - limits['last_reset_minute'] >= timedelta(minutes=1):
                        limits['queries_per_minute'] = 0
                        limits['last_reset_minute'] = now
                    
                    # Сброс часовых лимитов
                    if now - limits['last_reset_hour'] >= timedelta(hours=1):
                        limits['queries_per_minute'] = 0
                        limits['last_reset_hour'] = now
                
            except Exception as e:
                logger.error(f"Ошибка сброса лимитов: {e}")

    def _mark_expensive_query(self, query_hash: str, avg_time: float, max_time: float, call_count: int):
        """Отметить запрос как дорогой"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO expensive_queries 
                (query_hash, avg_execution_time, max_execution_time, call_count, last_seen)
                VALUES (?, ?, ?, ?, ?)
            ''', (query_hash, avg_time, max_time, call_count, datetime.now()))
            
            conn.commit()
            conn.close()
            
            self.expensive_queries.add(query_hash)
            
            # Создаем алерт
            self._create_security_alert(
                alert_type="EXPENSIVE_QUERY",
                severity="WARNING",
                message=f"Дорогой запрос обнаружен: среднее время {avg_time:.2f}с, максимум {max_time:.2f}с",
                query_hash=query_hash,
                details={
                    'avg_execution_time': avg_time,
                    'max_execution_time': max_time,
                    'call_count': call_count
                }
            )
            
        except Exception as e:
            logger.error(f"Ошибка отметки дорогого запроса: {e}")

    def _create_security_alert(self, alert_type: str, severity: str, message: str, 
                             user_id: Optional[int] = None, query_hash: Optional[str] = None,
                             details: Optional[Dict] = None):
        """Создание алерта безопасности"""
        alert = SecurityAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            user_id=user_id,
            query_hash=query_hash,
            details=details or {}
        )
        
        self.security_alerts.append(alert)
        
        # Сохраняем в БД
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_alerts 
                (alert_type, severity, message, user_id, query_hash, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_type, severity, message, user_id, query_hash, 
                  json.dumps(details) if details else None))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения алерта: {e}")
        
        # Логируем критичные алерты
        if severity in ['CRITICAL', 'HIGH']:
            logger.warning(f"SECURITY ALERT [{severity}]: {message}")

    def _hash_query(self, query: str) -> str:
        """Создание хеша запроса"""
        # Нормализуем запрос (убираем пробелы, приводим к нижнему регистру)
        normalized = re.sub(r'\s+', ' ', query.strip().lower())
        return hashlib.md5(normalized.encode()).hexdigest()

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Анализ запроса на предмет опасности"""
        analysis = {
            'is_dangerous': False,
            'risk_level': 'LOW',
            'warnings': [],
            'query_type': 'SELECT',
            'estimated_cost': 'LOW'
        }
        
        query_upper = query.upper().strip()
        
        # Определяем тип запроса
        if query_upper.startswith('SELECT'):
            analysis['query_type'] = 'SELECT'
        elif query_upper.startswith('INSERT'):
            analysis['query_type'] = 'INSERT'
        elif query_upper.startswith('UPDATE'):
            analysis['query_type'] = 'UPDATE'
        elif query_upper.startswith('DELETE'):
            analysis['query_type'] = 'DELETE'
        elif query_upper.startswith('DROP'):
            analysis['query_type'] = 'DROP'
        elif query_upper.startswith('CREATE'):
            analysis['query_type'] = 'CREATE'
        elif query_upper.startswith('ALTER'):
            analysis['query_type'] = 'ALTER'
        
        # Проверяем опасные паттерны
        for pattern in self.dangerous_patterns:
            if re.search(pattern, query_upper):
                analysis['is_dangerous'] = True
                analysis['risk_level'] = 'HIGH'
                analysis['warnings'].append(f"Обнаружен опасный паттерн: {pattern}")
        
        # Проверяем на SELECT *
        if 'SELECT *' in query_upper:
            analysis['warnings'].append("Использование SELECT * может быть неэффективным")
            analysis['estimated_cost'] = 'MEDIUM'
        
        # Проверяем на отсутствие WHERE в UPDATE/DELETE
        if analysis['query_type'] in ['UPDATE', 'DELETE'] and 'WHERE' not in query_upper:
            analysis['is_dangerous'] = True
            analysis['risk_level'] = 'CRITICAL'
            analysis['warnings'].append("UPDATE/DELETE без WHERE может затронуть все строки")
        
        # Проверяем на большие LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', query_upper)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > 10000:
                analysis['warnings'].append(f"Большой LIMIT ({limit_value}) может быть медленным")
                analysis['estimated_cost'] = 'HIGH'
        
        return analysis

    def _check_rate_limits(self, user_id: Optional[int]) -> bool:
        """Проверка лимитов частоты запросов"""
        if not self.config['enable_rate_limiting'] or user_id is None:
            return True
        
        limits = self.user_limits[user_id]
        now = datetime.now()
        
        # Проверяем минутный лимит
        if now - limits['last_reset_minute'] >= timedelta(minutes=1):
            limits['queries_per_minute'] = 0
            limits['last_reset_minute'] = now
        
        if limits['queries_per_minute'] >= self.config['max_queries_per_minute']:
            self._create_security_alert(
                alert_type="RATE_LIMIT_EXCEEDED",
                severity="WARNING",
                message=f"Превышен минутный лимит запросов: {limits['queries_per_minute']}",
                user_id=user_id
            )
            return False
        
        # Проверяем часовой лимит
        if now - limits['last_reset_hour'] >= timedelta(hours=1):
            limits['queries_per_hour'] = 0
            limits['last_reset_hour'] = now
        
        if limits['queries_per_hour'] >= self.config['max_queries_per_hour']:
            self._create_security_alert(
                alert_type="RATE_LIMIT_EXCEEDED",
                severity="HIGH",
                message=f"Превышен часовой лимит запросов: {limits['queries_per_hour']}",
                user_id=user_id
            )
            return False
        
        # Увеличиваем счетчики
        limits['queries_per_minute'] += 1
        limits['queries_per_hour'] += 1
        
        return True

    def _get_cached_result(self, query_hash: str) -> Optional[Any]:
        """Получение результата из кэша"""
        if not self.config['enable_caching']:
            return None
        
        if query_hash in self.query_cache:
            cached_data, timestamp = self.query_cache[query_hash]
            if time.time() - timestamp < self.config['cache_ttl']:
                return cached_data
            else:
                del self.query_cache[query_hash]
        
        return None

    def _cache_result(self, query_hash: str, result: Any):
        """Сохранение результата в кэш"""
        if not self.config['enable_caching']:
            return
        
        self.query_cache[query_hash] = (result, time.time())

    def execute_protected_query(self, query: str, params: Optional[Tuple] = None, 
                              user_id: Optional[int] = None) -> Tuple[Any, Dict[str, Any]]:
        """Выполнение защищенного SQL-запроса"""
        start_time = time.time()
        query_hash = self._hash_query(query)
        
        # Проверяем, не заблокирован ли запрос
        if query_hash in self.blocked_queries:
            self._create_security_alert(
                alert_type="BLOCKED_QUERY_ATTEMPT",
                severity="HIGH",
                message="Попытка выполнения заблокированного запроса",
                user_id=user_id,
                query_hash=query_hash
            )
            raise Exception("Запрос заблокирован из-за низкой производительности")
        
        # Проверяем лимиты частоты
        if not self._check_rate_limits(user_id):
            raise Exception("Превышен лимит частоты запросов")
        
        # Анализируем запрос
        if self.config['enable_query_analysis']:
            analysis = self._analyze_query(query)
            if analysis['is_dangerous']:
                self._create_security_alert(
                    alert_type="DANGEROUS_QUERY",
                    severity=analysis['risk_level'],
                    message=f"Обнаружен опасный запрос: {', '.join(analysis['warnings'])}",
                    user_id=user_id,
                    query_hash=query_hash,
                    details=analysis
                )
        
        # Проверяем кэш
        cached_result = self._get_cached_result(query_hash)
        if cached_result is not None:
            logger.info(f"Результат получен из кэша для запроса {query_hash[:8]}...")
            return cached_result, {'from_cache': True, 'execution_time': 0}
        
        # Выполняем запрос
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Получаем результат
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
                self._create_security_alert(
                    alert_type="SLOW_QUERY",
                    severity="WARNING",
                    message=f"Медленный запрос: {execution_time:.2f}с",
                    user_id=user_id,
                    query_hash=query_hash,
                    details={'execution_time': execution_time}
                )
            
            # Проверяем количество строк
            if rows_affected > self.config['max_rows_per_query']:
                self._create_security_alert(
                    alert_type="LARGE_RESULT_SET",
                    severity="WARNING",
                    message=f"Большой результат: {rows_affected} строк",
                    user_id=user_id,
                    query_hash=query_hash,
                    details={'rows_affected': rows_affected}
                )
            
            # Создаем метрику
            metric = QueryMetrics(
                query_hash=query_hash,
                execution_time=execution_time,
                rows_affected=rows_affected,
                timestamp=datetime.now(),
                user_id=user_id,
                query_type=analysis.get('query_type', 'unknown'),
                is_expensive=execution_time > self.config['expensive_query_threshold']
            )
            
            self.query_metrics.append(metric)
            
            # Сохраняем метрику в БД
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO query_metrics 
                    (query_hash, execution_time, rows_affected, user_id, query_type, is_expensive)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (query_hash, execution_time, rows_affected, user_id, 
                      metric.query_type, metric.is_expensive))
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Ошибка сохранения метрики: {e}")
            
            # Кэшируем результат для SELECT запросов
            if query.strip().upper().startswith('SELECT'):
                self._cache_result(query_hash, result)
            
            return result, {
                'execution_time': execution_time,
                'rows_affected': rows_affected,
                'query_hash': query_hash,
                'from_cache': False
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Создаем алерт об ошибке
            self._create_security_alert(
                alert_type="QUERY_ERROR",
                severity="ERROR",
                message=f"Ошибка выполнения запроса: {str(e)}",
                user_id=user_id,
                query_hash=query_hash,
                details={'error': str(e), 'execution_time': execution_time}
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
        
        # Статистика по типам запросов
        query_types = defaultdict(int)
        for metric in recent_metrics:
            query_types[metric.query_type] += 1
        
        # Топ медленных запросов
        slow_queries = sorted(recent_metrics, key=lambda x: x.execution_time, reverse=True)[:5]
        
        return {
            'total_queries': total_queries,
            'avg_execution_time': round(avg_execution_time, 3),
            'max_execution_time': round(max_execution_time, 3),
            'expensive_queries_count': expensive_queries_count,
            'expensive_queries_percentage': round(expensive_queries_count / total_queries * 100, 1),
            'query_types': dict(query_types),
            'slow_queries': [
                {
                    'query_hash': m.query_hash[:8] + '...',
                    'execution_time': round(m.execution_time, 3),
                    'rows_affected': m.rows_affected,
                    'timestamp': m.timestamp.isoformat()
                }
                for m in slow_queries
            ]
        }

    def get_security_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение последних алертов безопасности"""
        recent_alerts = list(self.security_alerts)[-limit:]
        
        return [
            {
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'user_id': alert.user_id,
                'query_hash': alert.query_hash,
                'details': alert.details
            }
            for alert in recent_alerts
        ]

    def block_expensive_query(self, query_hash: str, reason: str = "Low performance"):
        """Заблокировать дорогой запрос"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE expensive_queries 
                SET is_blocked = TRUE 
                WHERE query_hash = ?
            ''', (query_hash,))
            
            conn.commit()
            conn.close()
            
            self.blocked_queries.add(query_hash)
            
            self._create_security_alert(
                alert_type="QUERY_BLOCKED",
                severity="INFO",
                message=f"Запрос заблокирован: {reason}",
                query_hash=query_hash,
                details={'reason': reason}
            )
            
            logger.info(f"Запрос {query_hash[:8]}... заблокирован: {reason}")
            
        except Exception as e:
            logger.error(f"Ошибка блокировки запроса: {e}")

    def unblock_query(self, query_hash: str):
        """Разблокировать запрос"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE expensive_queries 
                SET is_blocked = FALSE 
                WHERE query_hash = ?
            ''', (query_hash,))
            
            conn.commit()
            conn.close()
            
            self.blocked_queries.discard(query_hash)
            
            logger.info(f"Запрос {query_hash[:8]}... разблокирован")
            
        except Exception as e:
            logger.error(f"Ошибка разблокировки запроса: {e}")

    def update_config(self, new_config: Dict[str, Any]):
        """Обновление конфигурации"""
        self.config.update(new_config)
        logger.info(f"Конфигурация обновлена: {new_config}")

# Декоратор для автоматической защиты SQL-запросов
def protected_sql_query(user_id: Optional[int] = None):
    """Декоратор для защиты SQL-запросов"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Получаем систему защиты из глобального контекста или создаем новую
            protection_system = getattr(wrapper, '_protection_system', None)
            if protection_system is None:
                protection_system = SQLProtectionSystem()
                wrapper._protection_system = protection_system
            
            # Выполняем функцию с защитой
            return protection_system.execute_protected_query(
                func(*args, **kwargs), 
                user_id=user_id
            )
        return wrapper
    return decorator

# Пример использования
if __name__ == "__main__":
    # Создаем систему защиты
    protection = SQLProtectionSystem()
    
    # Тестируем защищенный запрос
    try:
        result, metrics = protection.execute_protected_query(
            "SELECT * FROM clients WHERE telegram_id = ?",
            (12345,),
            user_id=12345
        )
        print(f"Результат: {len(result)} строк, время: {metrics['execution_time']:.3f}с")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Получаем статистику
    stats = protection.get_performance_stats()
    print(f"Статистика: {stats}")
    
    # Получаем алерты
    alerts = protection.get_security_alerts()
    print(f"Алерты: {len(alerts)}")