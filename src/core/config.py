"""
Конфигурация бота
"""

import os
from dataclasses import dataclass
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Конфигурация бота"""
    
    # API ключи
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PAYMENT_TOKEN: str = os.getenv("PAYMENT_TOKEN", "")
    
    # Настройки токенов
    MAX_TOKENS: int = 4000
    CONTEXT_WINDOW: int = 3000
    RESPONSE_TOKENS: int = 1000
    MIN_TOKENS: int = 100
    
    # Настройки сообщений
    MAX_MESSAGE_LENGTH: int = 4000
    MAX_CONVERSATION_LENGTH: int = 15
    
    # Настройки кэширования
    CACHE_TTL: int = 3600  # 1 час
    CACHE_SIZE: int = 1000
    
    # Настройки мониторинга
    MONITORING_ENABLED: bool = True
    AUTO_OPTIMIZATION: bool = True
    
    # Настройки A/B тестирования
    AB_TESTING_ENABLED: bool = True
    MIN_SAMPLES_FOR_AB: int = 10
    
    # Настройки базы данных
    DATABASE_PATH: str = "psychoanalyst.db"
    
    def __post_init__(self):
        """Валидация конфигурации"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения")
    
    def get_user_limits(self, user_type: str = "free") -> Dict[str, int]:
        """Получить лимиты для типа пользователя"""
        limits = {
            "free": {
                "max_tokens": self.MAX_TOKENS,
                "max_messages": 10,
                "cache_ttl": self.CACHE_TTL
            },
            "premium": {
                "max_tokens": self.MAX_TOKENS + 1000,
                "max_messages": 20,
                "cache_ttl": self.CACHE_TTL * 2
            }
        }
        return limits.get(user_type, limits["free"])
    
    def get_adaptive_limits(self, conversation_length: int, user_type: str = "free") -> Dict[str, int]:
        """Получить адаптивные лимиты на основе контекста"""
        base_limits = self.get_user_limits(user_type)
        
        # Адаптация на основе длины диалога
        if conversation_length > 15:
            base_limits["max_tokens"] = max(
                self.MIN_TOKENS,
                base_limits["max_tokens"] - 500
            )
        elif conversation_length < 5:
            base_limits["max_tokens"] = min(
                self.MAX_TOKENS + 500,
                base_limits["max_tokens"] + 200
            )
        
        return base_limits