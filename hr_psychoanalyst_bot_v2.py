#!/usr/bin/env python3
"""
HR-Психоаналитик Бот v2.0
Улучшенная версия с интегрированным управлением токенами и автоматической оптимизацией
"""

import asyncio
import logging
import sys
import os

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.config import Config
from src.core.bot import HRPsychoanalystBot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация конфигурации
        config = Config()
        
        # Создание и запуск бота
        bot = HRPsychoanalystBot(config)
        
        # Запуск бота
        await bot.start()
        
        # Ожидание завершения
        try:
            # Бот работает до получения сигнала остановки
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        finally:
            await bot.stop()
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Запуск бота
    asyncio.run(main())