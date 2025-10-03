#!/usr/bin/env python3
"""
Продвинутая система кэширования для дорогих SQL-операций
Включает многоуровневое кэширование, инвалидацию и оптимизацию
"""

import sqlite3
import time
import json
import hashlib
import threading
import pickle
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import functools
import weakref

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Запись кэша"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0
    tags: List[str] = None
    dependencies: List[str] = None

@dataclass
class CacheStats:
    """Статистика кэша"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0

class MultiLevelCache:
    """Многоуровневая система кэширования"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.l1_cache = OrderedDict()  # L1: Быстрый кэш в памяти
        self.l2_cache = {}  # L2: Кэш в БД
        self.cache_stats = CacheStats()
        self.max_l1_size = 1000  # Максимум записей в L1
        self.max_l1_memory = 100 * 1024 * 1024  # 100MB максимум для L1
        self.default_ttl = 300  # 5 минут по умолчанию
        self.lock = threading.RLock()
        
        # Индексы для быстрого поиска
        self.tag_index = defaultdict(set)  # tag -> set of keys
        self.dependency_index = defaultdict(set)  # dependency -> set of keys
        
        # Инициализация БД для L2 кэша
        self._init_cache_database()
        
        # Запуск фоновых задач
        self._start_background_tasks()
    
    def _init_cache_database(self):
        """Инициализация БД для кэша"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_l2 (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                size_bytes INTEGER DEFAULT 0,
                tags TEXT,
                dependencies TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_expires 
            ON cache_l2(expires_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_tags 
            ON cache_l2(tags)
        ''')
        
        conn.commit()
        conn.close()
    
    def _start_background_tasks(self):
        """Запуск фоновых задач"""
        # Очистка истекших записей
        cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        cleanup_thread.start()
        
        # Синхронизация L1 и L2
        sync_thread = threading.Thread(target=self._sync_caches, daemon=True)
        sync_thread.start()
        
        # Мониторинг производительности
        monitor_thread = threading.Thread(target=self._monitor_performance, daemon=True)
        monitor_thread.start()
    
    def _cleanup_expired(self):
        """Очистка истекших записей"""
        while True:
            try:
                time.sleep(60)  # Каждую минуту
                
                with self.lock:
                    now = datetime.now()
                    
                    # Очистка L1
                    expired_keys = []
                    for key, entry in self.l1_cache.items():
                        if entry.expires_at and entry.expires_at < now:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        self._remove_from_l1(key)
                    
                    # Очистка L2
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        DELETE FROM cache_l2 
                        WHERE expires_at IS NOT NULL AND expires_at < ?
                    ''', (now,))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    conn.close()
                    
                    if expired_keys or deleted_count > 0:
                        logger.info(f"Очищено истекших записей: L1={len(expired_keys)}, L2={deleted_count}")
                
            except Exception as e:
                logger.error(f"Ошибка очистки кэша: {e}")
    
    def _sync_caches(self):
        """Синхронизация L1 и L2 кэшей"""
        while True:
            try:
                time.sleep(30)  # Каждые 30 секунд
                
                with self.lock:
                    # Загружаем популярные записи из L2 в L1
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT key, value, created_at, expires_at, access_count, 
                               last_accessed, size_bytes, tags, dependencies
                        FROM cache_l2 
                        WHERE access_count > 5
                        ORDER BY access_count DESC, last_accessed DESC
                        LIMIT 100
                    ''')
                    
                    for row in cursor.fetchall():
                        key = row[0]
                        if key not in self.l1_cache:
                            entry = CacheEntry(
                                key=key,
                                value=pickle.loads(row[1]),
                                created_at=datetime.fromisoformat(row[2]),
                                expires_at=datetime.fromisoformat(row[3]) if row[3] else None,
                                access_count=row[4],
                                last_accessed=datetime.fromisoformat(row[5]) if row[5] else None,
                                size_bytes=row[6],
                                tags=json.loads(row[7]) if row[7] else [],
                                dependencies=json.loads(row[8]) if row[8] else []
                            )
                            self._add_to_l1(entry)
                    
                    conn.close()
                
            except Exception as e:
                logger.error(f"Ошибка синхронизации кэшей: {e}")
    
    def _monitor_performance(self):
        """Мониторинг производительности кэша"""
        while True:
            try:
                time.sleep(300)  # Каждые 5 минут
                
                with self.lock:
                    total_requests = self.cache_stats.hits + self.cache_stats.misses
                    if total_requests > 0:
                        self.cache_stats.hit_rate = self.cache_stats.hits / total_requests
                    
                    logger.info(f"Статистика кэша: "
                              f"Hit rate: {self.cache_stats.hit_rate:.2%}, "
                              f"L1 entries: {len(self.l1_cache)}, "
                              f"Total size: {self.cache_stats.total_size_bytes / 1024 / 1024:.1f}MB")
                
            except Exception as e:
                logger.error(f"Ошибка мониторинга кэша: {e}")
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict, 
                     tags: List[str] = None) -> str:
        """Генерация ключа кэша"""
        # Создаем хеш из функции, аргументов и тегов
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {},
            'tags': sorted(tags) if tags else []
        }
        
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _calculate_size(self, value: Any) -> int:
        """Вычисление размера значения в байтах"""
        try:
            return len(pickle.dumps(value))
        except:
            return 0
    
    def _add_to_l1(self, entry: CacheEntry):
        """Добавление записи в L1 кэш"""
        # Проверяем лимиты
        while (len(self.l1_cache) >= self.max_l1_size or 
               self.cache_stats.total_size_bytes >= self.max_l1_memory):
            self._evict_lru()
        
        # Добавляем запись
        self.l1_cache[entry.key] = entry
        self.cache_stats.total_size_bytes += entry.size_bytes
        self.cache_stats.entry_count += 1
        
        # Обновляем индексы
        if entry.tags:
            for tag in entry.tags:
                self.tag_index[tag].add(entry.key)
        
        if entry.dependencies:
            for dep in entry.dependencies:
                self.dependency_index[dep].add(entry.key)
    
    def _remove_from_l1(self, key: str):
        """Удаление записи из L1 кэша"""
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            del self.l1_cache[key]
            self.cache_stats.total_size_bytes -= entry.size_bytes
            self.cache_stats.entry_count -= 1
            
            # Обновляем индексы
            if entry.tags:
                for tag in entry.tags:
                    self.tag_index[tag].discard(key)
            
            if entry.dependencies:
                for dep in entry.dependencies:
                    self.dependency_index[dep].discard(key)
    
    def _evict_lru(self):
        """Удаление наименее используемой записи"""
        if not self.l1_cache:
            return
        
        # Удаляем самую старую запись (LRU)
        key, entry = self.l1_cache.popitem(last=False)
        self.cache_stats.total_size_bytes -= entry.size_bytes
        self.cache_stats.entry_count -= 1
        self.cache_stats.evictions += 1
        
        # Обновляем индексы
        if entry.tags:
            for tag in entry.tags:
                self.tag_index[tag].discard(key)
        
        if entry.dependencies:
            for dep in entry.dependencies:
                self.dependency_index[dep].discard(key)
    
    def _save_to_l2(self, entry: CacheEntry):
        """Сохранение записи в L2 кэш (БД)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO cache_l2 
                (key, value, created_at, expires_at, access_count, 
                 last_accessed, size_bytes, tags, dependencies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.key,
                pickle.dumps(entry.value),
                entry.created_at.isoformat(),
                entry.expires_at.isoformat() if entry.expires_at else None,
                entry.access_count,
                entry.last_accessed.isoformat() if entry.last_accessed else None,
                entry.size_bytes,
                json.dumps(entry.tags) if entry.tags else None,
                json.dumps(entry.dependencies) if entry.dependencies else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения в L2 кэш: {e}")
    
    def _load_from_l2(self, key: str) -> Optional[CacheEntry]:
        """Загрузка записи из L2 кэша"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT value, created_at, expires_at, access_count, 
                       last_accessed, size_bytes, tags, dependencies
                FROM cache_l2 
                WHERE key = ?
            ''', (key,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                entry = CacheEntry(
                    key=key,
                    value=pickle.loads(row[0]),
                    created_at=datetime.fromisoformat(row[1]),
                    expires_at=datetime.fromisoformat(row[2]) if row[2] else None,
                    access_count=row[3],
                    last_accessed=datetime.fromisoformat(row[4]) if row[4] else None,
                    size_bytes=row[5],
                    tags=json.loads(row[6]) if row[6] else [],
                    dependencies=json.loads(row[7]) if row[7] else []
                )
                
                # Обновляем статистику доступа
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self._save_to_l2(entry)
                
                return entry
            
        except Exception as e:
            logger.error(f"Ошибка загрузки из L2 кэш: {e}")
        
        return None
    
    def get(self, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        with self.lock:
            # Проверяем L1 кэш
            if key in self.l1_cache:
                entry = self.l1_cache[key]
                
                # Проверяем срок действия
                if entry.expires_at and entry.expires_at < datetime.now():
                    self._remove_from_l1(key)
                    return None
                
                # Обновляем статистику доступа
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                
                # Перемещаем в конец (LRU)
                self.l1_cache.move_to_end(key)
                
                self.cache_stats.hits += 1
                return entry.value
            
            # Проверяем L2 кэш
            entry = self._load_from_l2(key)
            if entry:
                # Проверяем срок действия
                if entry.expires_at and entry.expires_at < datetime.now():
                    return None
                
                # Добавляем в L1 кэш
                self._add_to_l1(entry)
                
                self.cache_stats.hits += 1
                return entry.value
            
            self.cache_stats.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            tags: List[str] = None, dependencies: List[str] = None):
        """Сохранение значения в кэш"""
        with self.lock:
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl or self.default_ttl)
            size_bytes = self._calculate_size(value)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at,
                access_count=0,
                last_accessed=now,
                size_bytes=size_bytes,
                tags=tags or [],
                dependencies=dependencies or []
            )
            
            # Добавляем в L1 кэш
            self._add_to_l1(entry)
            
            # Сохраняем в L2 кэш
            self._save_to_l2(entry)
    
    def delete(self, key: str):
        """Удаление записи из кэша"""
        with self.lock:
            # Удаляем из L1
            self._remove_from_l1(key)
            
            # Удаляем из L2
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM cache_l2 WHERE key = ?', (key,))
                conn.commit()
                conn.close()
                
            except Exception as e:
                logger.error(f"Ошибка удаления из L2 кэш: {e}")
    
    def invalidate_by_tag(self, tag: str):
        """Инвалидация кэша по тегу"""
        with self.lock:
            keys_to_remove = list(self.tag_index.get(tag, set()))
            
            for key in keys_to_remove:
                self.delete(key)
            
            logger.info(f"Инвалидированы записи с тегом '{tag}': {len(keys_to_remove)}")
    
    def invalidate_by_dependency(self, dependency: str):
        """Инвалидация кэша по зависимости"""
        with self.lock:
            keys_to_remove = list(self.dependency_index.get(dependency, set()))
            
            for key in keys_to_remove:
                self.delete(key)
            
            logger.info(f"Инвалидированы записи с зависимостью '{dependency}': {len(keys_to_remove)}")
    
    def clear(self):
        """Очистка всего кэша"""
        with self.lock:
            # Очищаем L1
            self.l1_cache.clear()
            self.tag_index.clear()
            self.dependency_index.clear()
            self.cache_stats = CacheStats()
            
            # Очищаем L2
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM cache_l2')
                conn.commit()
                conn.close()
                
            except Exception as e:
                logger.error(f"Ошибка очистки L2 кэш: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        with self.lock:
            total_requests = self.cache_stats.hits + self.cache_stats.misses
            hit_rate = self.cache_stats.hits / total_requests if total_requests > 0 else 0
            
            return {
                'hits': self.cache_stats.hits,
                'misses': self.cache_stats.misses,
                'hit_rate': round(hit_rate, 3),
                'evictions': self.cache_stats.evictions,
                'l1_entries': len(self.l1_cache),
                'total_size_mb': round(self.cache_stats.total_size_bytes / 1024 / 1024, 2),
                'max_l1_size': self.max_l1_size,
                'max_l1_memory_mb': round(self.max_l1_memory / 1024 / 1024, 2)
            }

# Глобальный экземпляр кэша
_global_cache = None

def get_cache() -> MultiLevelCache:
    """Получение глобального экземпляра кэша"""
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiLevelCache()
    return _global_cache

# Декоратор для кэширования функций
def cached(ttl: Optional[int] = None, tags: List[str] = None, 
          dependencies: List[str] = None, cache_key: Optional[str] = None):
    """Декоратор для кэширования результатов функций"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Генерируем ключ кэша
            if cache_key:
                key = cache_key
            else:
                key = cache._generate_key(func.__name__, args, kwargs, tags)
            
            # Пытаемся получить из кэша
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Выполняем функцию
            logger.debug(f"Cache miss for {func.__name__}, executing...")
            result = func(*args, **kwargs)
            
            # Сохраняем в кэш
            cache.set(key, result, ttl, tags, dependencies)
            
            return result
        
        # Добавляем методы для управления кэшем
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_invalidate = lambda tag: cache.invalidate_by_tag(tag)
        wrapper.cache_stats = lambda: cache.get_stats()
        
        return wrapper
    return decorator

# Специализированные декораторы для SQL-запросов
def cached_sql_query(ttl: int = 300, tags: List[str] = None):
    """Декоратор для кэширования SQL-запросов"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Создаем ключ на основе SQL-запроса и параметров
            sql_query = args[0] if args else ""
            params = args[1] if len(args) > 1 else ()
            
            key_data = {
                'sql': sql_query,
                'params': params,
                'tags': tags or []
            }
            
            key = hashlib.md5(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()
            
            # Пытаемся получить из кэша
            result = cache.get(key)
            if result is not None:
                logger.info(f"SQL cache hit for query: {sql_query[:50]}...")
                return result
            
            # Выполняем SQL-запрос
            logger.info(f"SQL cache miss, executing: {sql_query[:50]}...")
            result = func(*args, **kwargs)
            
            # Кэшируем только SELECT запросы
            if sql_query.strip().upper().startswith('SELECT'):
                cache.set(key, result, ttl, tags, ['sql_database'])
            
            return result
        
        return wrapper
    return decorator

# Пример использования
if __name__ == "__main__":
    # Создаем кэш
    cache = MultiLevelCache()
    
    # Тестируем кэширование
    @cached(ttl=60, tags=['test'])
    def expensive_calculation(n: int) -> int:
        time.sleep(1)  # Имитируем дорогую операцию
        return n * n
    
    # Первый вызов - медленный
    start = time.time()
    result1 = expensive_calculation(5)
    time1 = time.time() - start
    print(f"Первый вызов: {result1}, время: {time1:.2f}с")
    
    # Второй вызов - быстрый (из кэша)
    start = time.time()
    result2 = expensive_calculation(5)
    time2 = time.time() - start
    print(f"Второй вызов: {result2}, время: {time2:.2f}с")
    
    # Статистика кэша
    stats = cache.get_stats()
    print(f"Статистика кэша: {stats}")
    
    # Инвалидация по тегу
    cache.invalidate_by_tag('test')
    print("Кэш инвалидирован по тегу 'test'")
    
    # Очистка кэша
    cache.clear()
    print("Кэш очищен")