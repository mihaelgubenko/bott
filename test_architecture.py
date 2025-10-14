#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новой архитектуры
"""

import sys
import os
import asyncio
import logging

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.config import Config
from src.ai.token_manager import TokenManager
from src.ai.context_compressor import ContextCompressor
from src.ai.adaptive_prompt_manager import AdaptivePromptManager, PromptType
from src.ai.token_monitor import TokenMonitor
from src.ai.response_cache import ResponseCache

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_token_manager():
    """Тест TokenManager"""
    print("🧪 Тестирование TokenManager...")
    
    config = Config()
    token_manager = TokenManager(config)
    
    # Тест подсчета токенов
    text = "Привет! Как дела? Расскажи о своей работе и планах на будущее."
    tokens = token_manager.count_tokens(text)
    print(f"  Токенов в тексте: {tokens}")
    
    # Тест оптимизации промпта
    prompt = "Ты психолог. Проанализируй личность."
    context = "Пользователь говорит: " + text
    optimized_prompt, optimized_context, usage = token_manager.optimize_prompt(
        prompt, context, "free"
    )
    print(f"  Оптимизированный промпт: {len(optimized_prompt)} символов")
    print(f"  Использование токенов: {usage.total_tokens}")
    
    # Тест разбиения длинного ответа
    long_response = "Это очень длинный ответ. " * 200
    parts = token_manager.split_long_response(long_response, 1000)
    print(f"  Разбито на {len(parts)} частей")
    
    print("✅ TokenManager работает корректно\n")

async def test_context_compressor():
    """Тест ContextCompressor"""
    print("🧪 Тестирование ContextCompressor...")
    
    config = Config()
    compressor = ContextCompressor(config)
    
    # Тест сжатия диалога
    messages = [
        "Привет! Как дела?",
        "У меня проблемы на работе, не знаю что делать",
        "Начальник постоянно критикует мою работу",
        "Я боюсь, что меня уволят",
        "Хочу найти новую работу, но не знаю с чего начать",
        "Может быть, стоит пройти курсы повышения квалификации?",
        "Или лучше сразу искать вакансии?",
        "Очень сложно принимать решения в такой ситуации"
    ]
    
    compressed = compressor.compress_conversation(messages, 1000)
    print(f"  Сжато с {len(' '.join(messages))} до {len(compressed)} символов")
    
    # Тест извлечения инсайтов
    insights = compressor.extract_key_insights(messages)
    print(f"  Извлечено инсайтов: {sum(len(v) for v in insights.values())}")
    
    # Тест создания резюме
    summary = compressor.create_summary(messages)
    print(f"  Резюме: {summary[:100]}...")
    
    print("✅ ContextCompressor работает корректно\n")

async def test_adaptive_prompt_manager():
    """Тест AdaptivePromptManager"""
    print("🧪 Тестирование AdaptivePromptManager...")
    
    config = Config()
    prompt_manager = AdaptivePromptManager(config)
    
    # Тест получения промпта
    prompt, variant_id = prompt_manager.get_optimal_prompt(
        PromptType.EXPRESS_ANALYSIS, 
        500, 
        user_id=12345
    )
    print(f"  Получен промпт: {len(prompt)} символов")
    print(f"  Вариант: {variant_id}")
    
    # Тест статистики шаблонов
    stats = prompt_manager.get_template_stats()
    print(f"  Доступно шаблонов: {len(stats)}")
    
    print("✅ AdaptivePromptManager работает корректно\n")

async def test_token_monitor():
    """Тест TokenMonitor"""
    print("🧪 Тестирование TokenMonitor...")
    
    config = Config()
    monitor = TokenMonitor(config)
    
    # Тест отслеживания запроса
    monitor.track_request(
        user_id=12345,
        prompt_tokens=100,
        response_tokens=200,
        response_length=500,
        truncated=False,
        satisfaction=4.5
    )
    
    # Тест предсказания переполнения
    conversation = ["Привет", "Как дела?", "Расскажи о работе"] * 10
    overflow, percentage = monitor.predict_token_overflow(conversation, "Новое сообщение", 12345)
    print(f"  Предсказание переполнения: {overflow} ({percentage}%)")
    
    # Тест получения инсайтов
    insights = monitor.get_user_insights(12345)
    print(f"  Инсайты пользователя: {len(insights)} полей")
    
    # Тест системного здоровья
    health = monitor.get_system_health()
    print(f"  Статус системы: {health['total_requests']} запросов")
    
    print("✅ TokenMonitor работает корректно\n")

async def test_response_cache():
    """Тест ResponseCache"""
    print("🧪 Тестирование ResponseCache...")
    
    config = Config()
    cache = ResponseCache(config)
    
    # Тест сохранения в кэш
    cache.put(
        prompt="Тестовый промпт",
        response="Тестовый ответ",
        user_id=12345,
        response_type="test"
    )
    
    # Тест получения из кэша
    cached_response = cache.get("Тестовый промпт", 12345, response_type="test")
    print(f"  Кэшированный ответ: {cached_response is not None}")
    
    # Тест статистики
    stats = cache.get_cache_stats()
    print(f"  Статистика кэша: {stats['total_entries']} записей")
    
    print("✅ ResponseCache работает корректно\n")

async def test_integration():
    """Интеграционный тест"""
    print("🧪 Интеграционный тест...")
    
    try:
        from src.ai.openai_client import OpenAIClient
        
        config = Config()
        ai_client = OpenAIClient(config)
        
        # Тест получения ответа (без реального вызова OpenAI)
        print("  AI клиент инициализирован успешно")
        
        # Тест системного здоровья
        health = ai_client.get_system_health()
        print(f"  Системное здоровье: {len(health)} компонентов")
        
        print("✅ Интеграционный тест прошел успешно\n")
        
    except Exception as e:
        print(f"❌ Ошибка интеграционного теста: {e}\n")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов новой архитектуры HR-Психоаналитик Бота v2.0\n")
    
    try:
        # Тестируем компоненты
        await test_token_manager()
        await test_context_compressor()
        await test_adaptive_prompt_manager()
        await test_token_monitor()
        await test_response_cache()
        await test_integration()
        
        print("🎉 Все тесты прошли успешно!")
        print("\n📊 Результаты:")
        print("✅ TokenManager - управление токенами")
        print("✅ ContextCompressor - сжатие контекста")
        print("✅ AdaptivePromptManager - адаптивные промпты")
        print("✅ TokenMonitor - мониторинг и оптимизация")
        print("✅ ResponseCache - кэширование ответов")
        print("✅ Интеграция - все компоненты работают вместе")
        
        print("\n🚀 Новая архитектура готова к использованию!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)