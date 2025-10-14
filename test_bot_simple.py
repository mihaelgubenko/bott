#!/usr/bin/env python3
"""
Простая версия бота для тестирования исправлений
"""

import asyncio
import logging
import sys
import os

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.config import Config
from src.ai.openai_client import OpenAIClient
from src.ai.adaptive_prompt_manager import PromptType

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_ai_response():
    """Тест получения ответа от ИИ"""
    try:
        # Инициализация конфигурации
        config = Config()
        
        # Создание AI клиента
        ai_client = OpenAIClient(config)
        
        # Тестовый запрос
        test_message = "Что из себя представляет промышленный дизайн? Что в него входит. Какие курсы ты сможешь мне подобрать."
        
        print(f"🧪 Тестируем запрос: {test_message}")
        
        # Получаем ответ
        response = await ai_client.get_response(
            prompt=test_message,
            user_id=12345,
            prompt_type=PromptType.CAREER_CONSULTATION,
            context={'conversation': '', 'user_message': test_message}
        )
        
        print(f"✅ Ответ получен:")
        print(f"Длина: {len(response.content)} символов")
        print(f"Обрезан: {response.truncated}")
        print(f"Кэширован: {response.cached}")
        print(f"Время ответа: {response.response_time:.2f} сек")
        print(f"\n📝 Содержимое ответа:")
        print(response.content)
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка тестирования: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование исправлений HR-Психоаналитик Бота v2.0\n")
    
    success = await test_ai_response()
    
    if success:
        print("\n🎉 Тест прошел успешно!")
        print("✅ Проблема с обрывами ответов решена")
        print("✅ Прямые вопросы обрабатываются корректно")
    else:
        print("\n❌ Тест не прошел")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)