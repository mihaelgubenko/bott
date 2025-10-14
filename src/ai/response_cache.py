"""
Кэш ответов для оптимизации производительности и снижения затрат
"""

import time
import hashlib
import logging
from typing import Dict, Optional, Any, Tuple, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)

@dataclass
class CachedResponse:
    """Кэшированный ответ"""
    response: str
    timestamp: datetime
    hit_count: int = 0
    user_id: int = 0
    prompt_hash: str = ""
    metadata: Dict[str, Any] = None

class ResponseCache:
    """Кэш ответов с интеллектуальным управлением"""
    
    def __init__(self, config):
        self.config = config
        self.cache = OrderedDict()  # LRU кэш
        self.max_size = config.CACHE_SIZE
        self.default_ttl = config.CACHE_TTL
        
        # Статистика кэша
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
        
        # Настройки TTL для разных типов ответов
        self.ttl_settings = {
            'express_analysis': 3600,  # 1 час
            'full_analysis': 7200,     # 2 часа
            'psychology_consultation': 1800,  # 30 минут
            'career_consultation': 3600,      # 1 час
            'default': config.CACHE_TTL
        }
    
    def _generate_cache_key(self, prompt: str, user_id: int, context: str = "") -> str:
        """Генерация ключа кэша"""
        # Создаем хэш на основе промпта, пользователя и контекста
        content = f"{prompt}|{user_id}|{context}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_expired(self, cached_response: CachedResponse, ttl: int) -> bool:
        """Проверка истечения срока действия кэша"""
        age = datetime.now() - cached_response.timestamp
        return age.total_seconds() > ttl
    
    def get(self, prompt: str, user_id: int, context: str = "", response_type: str = "default") -> Optional[str]:
        """Получение ответа из кэша"""
        
        self.stats['total_requests'] += 1
        
        cache_key = self._generate_cache_key(prompt, user_id, context)
        
        if cache_key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        cached_response = self.cache[cache_key]
        
        # Проверяем срок действия
        ttl = self.ttl_settings.get(response_type, self.default_ttl)
        if self._is_expired(cached_response, ttl):
            del self.cache[cache_key]
            self.stats['misses'] += 1
            logger.debug(f"Кэш истек для ключа {cache_key}")
            return None
        
        # Обновляем статистику использования
        cached_response.hit_count += 1
        self.stats['hits'] += 1
        
        # Перемещаем в конец (LRU)
        self.cache.move_to_end(cache_key)
        
        logger.debug(f"Кэш попадание для ключа {cache_key}")
        return cached_response.response
    
    def put(
        self, 
        prompt: str, 
        response: str, 
        user_id: int, 
        context: str = "",
        response_type: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Сохранение ответа в кэш"""
        
        cache_key = self._generate_cache_key(prompt, user_id, context)
        
        # Создаем кэшированный ответ
        cached_response = CachedResponse(
            response=response,
            timestamp=datetime.now(),
            user_id=user_id,
            prompt_hash=cache_key,
            metadata=metadata or {}
        )
        
        # Если ключ уже существует, обновляем
        if cache_key in self.cache:
            existing = self.cache[cache_key]
            cached_response.hit_count = existing.hit_count
        
        # Сохраняем в кэш
        self.cache[cache_key] = cached_response
        
        # Проверяем размер кэша
        if len(self.cache) > self.max_size:
            self._evict_oldest()
        
        logger.debug(f"Ответ сохранен в кэш с ключом {cache_key}")
        return cache_key
    
    def _evict_oldest(self):
        """Удаление самого старого элемента из кэша"""
        if not self.cache:
            return
        
        # Удаляем первый элемент (самый старый)
        oldest_key = next(iter(self.cache))
        del self.cache[oldest_key]
        self.stats['evictions'] += 1
        
        logger.debug(f"Удален из кэша ключ {oldest_key}")
    
    def invalidate_user(self, user_id: int):
        """Инвалидация кэша для конкретного пользователя"""
        
        keys_to_remove = [
            key for key, cached_response in self.cache.items()
            if cached_response.user_id == user_id
        ]
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Инвалидирован кэш для пользователя {user_id}, удалено {len(keys_to_remove)} записей")
    
    def invalidate_pattern(self, pattern: str):
        """Инвалидация кэша по паттерну в промпте"""
        
        keys_to_remove = []
        for key, cached_response in self.cache.items():
            if pattern.lower() in cached_response.response.lower():
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Инвалидирован кэш по паттерну '{pattern}', удалено {len(keys_to_remove)} записей")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        
        total_requests = self.stats['total_requests']
        hit_rate = (
            self.stats['hits'] / total_requests 
            if total_requests > 0 else 0
        )
        
        # Статистика по типам ответов
        type_stats = {}
        for cached_response in self.cache.values():
            response_type = cached_response.metadata.get('type', 'unknown')
            if response_type not in type_stats:
                type_stats[response_type] = {'count': 0, 'total_hits': 0}
            
            type_stats[response_type]['count'] += 1
            type_stats[response_type]['total_hits'] += cached_response.hit_count
        
        return {
            'total_entries': len(self.cache),
            'max_size': self.max_size,
            'hit_rate': hit_rate,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'type_stats': type_stats,
            'memory_usage_estimate': self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> int:
        """Примерная оценка использования памяти кэшем"""
        
        total_size = 0
        for cached_response in self.cache.values():
            # Примерная оценка размера записи
            response_size = len(cached_response.response.encode('utf-8'))
            metadata_size = len(str(cached_response.metadata).encode('utf-8'))
            total_size += response_size + metadata_size + 200  # +200 для служебных данных
        
        return total_size
    
    def get_popular_responses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение самых популярных ответов"""
        
        # Сортируем по количеству попаданий
        sorted_responses = sorted(
            self.cache.items(),
            key=lambda x: x[1].hit_count,
            reverse=True
        )
        
        popular = []
        for key, cached_response in sorted_responses[:limit]:
            popular.append({
                'key': key,
                'hit_count': cached_response.hit_count,
                'response_preview': cached_response.response[:100] + "..." if len(cached_response.response) > 100 else cached_response.response,
                'user_id': cached_response.user_id,
                'timestamp': cached_response.timestamp.isoformat(),
                'metadata': cached_response.metadata
            })
        
        return popular
    
    def cleanup_expired(self):
        """Очистка истекших записей"""
        
        current_time = datetime.now()
        expired_keys = []
        
        for key, cached_response in self.cache.items():
            response_type = cached_response.metadata.get('type', 'default')
            ttl = self.ttl_settings.get(response_type, self.default_ttl)
            
            if self._is_expired(cached_response, ttl):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Очищено {len(expired_keys)} истекших записей из кэша")
        
        return len(expired_keys)
    
    def clear(self):
        """Полная очистка кэша"""
        
        self.cache.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
        
        logger.info("Кэш полностью очищен")
    
    def export_cache(self) -> Dict[str, Any]:
        """Экспорт кэша для анализа"""
        
        return {
            'cache_entries': {
                key: {
                    'response': cached_response.response,
                    'timestamp': cached_response.timestamp.isoformat(),
                    'hit_count': cached_response.hit_count,
                    'user_id': cached_response.user_id,
                    'metadata': cached_response.metadata
                }
                for key, cached_response in self.cache.items()
            },
            'stats': self.stats,
            'settings': {
                'max_size': self.max_size,
                'default_ttl': self.default_ttl,
                'ttl_settings': self.ttl_settings
            }
        }
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Оптимизация кэша"""
        
        optimizations = {
            'entries_removed': 0,
            'memory_freed': 0,
            'recommendations': []
        }
        
        # Очищаем истекшие записи
        expired_count = self.cleanup_expired()
        optimizations['entries_removed'] += expired_count
        
        # Удаляем редко используемые записи
        if len(self.cache) > self.max_size * 0.8:
            # Сортируем по количеству попаданий
            sorted_by_hits = sorted(
                self.cache.items(),
                key=lambda x: x[1].hit_count
            )
            
            # Удаляем 20% самых редко используемых
            to_remove = int(len(self.cache) * 0.2)
            for key, _ in sorted_by_hits[:to_remove]:
                del self.cache[key]
                optimizations['entries_removed'] += 1
            
            optimizations['recommendations'].append(
                f"Удалено {to_remove} редко используемых записей"
            )
        
        # Рекомендации по настройке
        hit_rate = self.stats['hits'] / max(self.stats['total_requests'], 1)
        
        if hit_rate < 0.3:
            optimizations['recommendations'].append(
                "Низкий процент попаданий в кэш. Рассмотрите увеличение TTL или улучшение ключей кэширования"
            )
        
        if len(self.cache) > self.max_size * 0.9:
            optimizations['recommendations'].append(
                "Кэш почти заполнен. Рассмотрите увеличение max_size или более агрессивную очистку"
            )
        
        return optimizations