"""
Основной класс бота с интегрированным управлением токенами
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler as TGMessageHandler, ConversationHandler, filters

from .config import Config
from .database import DatabaseManager
from ..ai.openai_client import OpenAIClient
from ..ai.adaptive_prompt_manager import PromptType
from ..handlers.message_handler import MessageHandler
from ..handlers.analysis_handler import AnalysisHandler
from ..handlers.conversation_handler import ConversationHandler

logger = logging.getLogger(__name__)

class HRPsychoanalystBot:
    """Основной класс HR-Психоаналитик бота"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db = DatabaseManager(config)
        self.ai_client = OpenAIClient(config)
        
        # Инициализируем обработчики
        self.message_handler = MessageHandler(self.ai_client, self.db)
        self.analysis_handler = AnalysisHandler(self.ai_client, self.db)
        self.conversation_handler = ConversationHandler(self.ai_client, self.db)
        
        # Создаем приложение
        self.application = ApplicationBuilder().token(config.BOT_TOKEN).build()
        
        # Настраиваем обработчики
        self._setup_handlers()
        
        logger.info("HR-Психоаналитик бот инициализирован")
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Основные команды
        self.application.add_handler(CommandHandler('start', self.message_handler.start))
        self.application.add_handler(CommandHandler('help', self.message_handler.help_command))
        self.application.add_handler(CommandHandler('cancel', self.message_handler.cancel))
        self.application.add_handler(CommandHandler('reset', self.message_handler.reset_bot))
        
        # Анализ и консультации
        self.application.add_handler(CommandHandler('self_esteem', self.analysis_handler.start_self_esteem_test))
        self.application.add_handler(CommandHandler('consultation', self.message_handler.consultation_info))
        
        # Административные команды
        self.application.add_handler(CommandHandler('clear', self.message_handler.clear_memory))
        self.application.add_handler(CommandHandler('stats', self.message_handler.get_stats))
        self.application.add_handler(CommandHandler('optimize', self.message_handler.optimize_user))
        
        # Обработчик сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handler.handle_message)
        )
        
        # Обработчики состояний для анализа
        self._setup_conversation_handlers()
    
    def _setup_conversation_handlers(self):
        """Настройка обработчиков состояний диалога"""
        
        from telegram.ext import ConversationHandler
        
        # Обработчик для полного анализа
        full_analysis_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(r'полный анализ|детальный анализ'), 
                                       self.analysis_handler.start_full_analysis)],
            states={
                'Q1': [MessageHandler(filters.TEXT, self.analysis_handler.handle_full_analysis_answer)],
                'Q2': [MessageHandler(filters.TEXT, self.analysis_handler.handle_full_analysis_answer)],
                'Q3': [MessageHandler(filters.TEXT, self.analysis_handler.handle_full_analysis_answer)],
                'Q4': [MessageHandler(filters.TEXT, self.analysis_handler.handle_full_analysis_answer)],
                'Q5': [MessageHandler(filters.TEXT, self.analysis_handler.handle_full_analysis_answer)],
                'Q6': [MessageHandler(filters.TEXT, self.analysis_handler.handle_full_analysis_answer)],
                'Q7': [MessageHandler(filters.TEXT, self.analysis_handler.handle_full_analysis_answer)],
            },
            fallbacks=[CommandHandler('cancel', self.message_handler.cancel)],
            allow_reentry=True
        )
        
        # Обработчик для теста самооценки
        self_esteem_handler = ConversationHandler(
            entry_points=[CommandHandler('self_esteem', self.analysis_handler.start_self_esteem_test)],
            states={
                'SELF_ESTEEM_Q': [MessageHandler(filters.TEXT, self.analysis_handler.handle_self_esteem_answer)]
            },
            fallbacks=[CommandHandler('cancel', self.message_handler.cancel)],
            allow_reentry=True
        )
        
        self.application.add_handler(full_analysis_handler)
        self.application.add_handler(self_esteem_handler)
    
    async def start(self):
        """Запуск бота"""
        try:
            # Инициализируем базу данных
            await self.db.init_database()
            
            # Запускаем бота
            logger.info("Запуск HR-Психоаналитик бота...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Бот успешно запущен")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise
    
    async def stop(self):
        """Остановка бота"""
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Получение статуса здоровья бота"""
        return {
            'bot_status': 'running',
            'ai_client': self.ai_client.get_system_health(),
            'database': self.db.get_health_status(),
            'config': {
                'max_tokens': self.config.MAX_TOKENS,
                'cache_enabled': True,
                'monitoring_enabled': self.config.MONITORING_ENABLED
            }
        }
    
    def get_analytics(self) -> Dict[str, Any]:
        """Получение аналитики бота"""
        return self.ai_client.export_analytics()
    
    def optimize_system(self) -> Dict[str, Any]:
        """Оптимизация системы"""
        # Оптимизируем кэш
        cache_optimization = self.ai_client.response_cache.optimize_cache()
        
        # Получаем системную статистику
        system_health = self.get_health_status()
        
        return {
            'cache_optimization': cache_optimization,
            'system_health': system_health,
            'recommendations': self._get_system_recommendations()
        }
    
    def _get_system_recommendations(self) -> list:
        """Получение рекомендаций по оптимизации системы"""
        recommendations = []
        
        # Проверяем статистику кэша
        cache_stats = self.ai_client.response_cache.get_cache_stats()
        if cache_stats['hit_rate'] < 0.3:
            recommendations.append("Низкий процент попаданий в кэш. Рассмотрите увеличение TTL")
        
        # Проверяем статистику токенов
        token_stats = self.ai_client.token_monitor.get_system_health()
        if token_stats['truncation_rate'] > 0.15:
            recommendations.append("Высокий процент обрезанных ответов. Рекомендуется оптимизация промптов")
        
        return recommendations