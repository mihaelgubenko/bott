"""
Обработчик основных команд и сообщений бота
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

class MessageHandler:
    """Обработчик основных команд и сообщений"""
    
    def __init__(self, ai_client, database):
        self.ai_client = ai_client
        self.database = database
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Очищаем предыдущие данные пользователя
        self.ai_client.clear_user_data(user.id)
        
        welcome_text = (
            f"Привет, {user.first_name or 'друг'}! 👋\n\n"
            f"Я ваш *HR-психоаналитик* и карьерный консультант.\n\n"
            f"*Что я умею:*\n"
            f"🧠 Анализ личности и подбор карьеры\n"
            f"💙 Психологическая поддержка\n"
            f"📖 Тест самооценки (30 вопросов)\n"
            f"💼 Профессиональное развитие\n\n"
            f"*Команды:*\n"
            f"/self\\_esteem - Тест самооценки\n"
            f"/help - Справка\n"
            f"/consultation - Консультация\n\n"
            f"Просто напишите о том, что вас интересует!"
        )
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
        return 'WAITING_MESSAGE'
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        help_text = (
            "*СПРАВКА*\n\n"
            "*Бесплатно:*\n"
            "• Диалог и экспресс-анализ\n"
            "• Тест самооценки (30 вопросов)\n"
            "• Подбор карьеры\n\n"
            "*Платно (500₽):*\n"
            "• Полный психоанализ\n"
            "• Личная консультация\n\n"
            "*Команды:*\n"
            "/start \\- меню\n"
            "/self\\_esteem \\- тест\n"
            "/consultation \\- консультация\n"
            "/cancel \\- отменить\n\n"
            "Просто пишите о том, что беспокоит!"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /cancel"""
        user = update.effective_user
        
        # Очищаем данные пользователя
        self.ai_client.clear_user_data(user.id)
        
        await update.message.reply_text(
            "Анализ отменен. Для нового анализа используйте /start"
        )
        return 'END'
    
    async def reset_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /reset"""
        user = update.effective_user
        
        # Очищаем данные пользователя
        self.ai_client.clear_user_data(user.id)
        
        await update.message.reply_text(
            "🔄 Бот сброшен!\n\n"
            "Все ваши данные очищены. Начните заново с /start"
        )
    
    async def clear_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Очистка памяти бота (только для админов)"""
        user = update.effective_user
        
        # Проверка на админа (можно настроить)
        if user.id != 123456789:  # Замените на ваш Telegram ID
            await update.message.reply_text("❌ У вас нет прав для этой команды")
            return
        
        # Очистка всех данных
        self.ai_client.response_cache.clear()
        
        # Очистка базы данных
        try:
            await self.database.clear_all_data()
            
            await update.message.reply_text(
                "✅ Память бота полностью очищена:\n"
                "• Очищена RAM память\n"
                "• Очищена база данных\n"
                "• Все диалоги удалены\n\n"
                "💡 Для очистки кэша Telegram перезапустите бота командой /start"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при очистке: {e}")
    
    async def consultation_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Информация о личной консультации"""
        consultation_text = """
💫 **ЛИЧНАЯ КОНСУЛЬТАЦИЯ**

Я помогу вам пройти путь трансформации и раскрыть ваш истинный потенциал.

**Что я предлагаю:**

✨ **Повышение самооценки**
• Избавление от самокритики и сомнений
• Обретение уверенности в себе
• Принятие и любовь к себе

🎯 **Поиск предназначения**
• Обнаружение вашего уникального дара
• Определение жизненной миссии
• Построение карьеры по призванию

😌 **Освобождение от негатива**
• Проработка страхов и тревог
• Трансформация гнева в силу
• Освобождение от обид прошлого

💝 **Гармонизация отношений**
• Улучшение отношений с близкими
• Установление здоровых границ
• Привлечение качественных отношений

━━━━━━━━━━━━━━━━━━━━━━

**Формат работы:**
• Индивидуальные сессии 1-2 часа
• Онлайн/оффлайн (на ваш выбор)
• Персональная программа развития
• Поддержка между сессиями

**Стоимость:** обсуждается индивидуально

📞 **Записаться:**
Напишите мне: [Ваш Telegram/Email/Телефон]

Или просто напишите "Хочу консультацию" здесь!

━━━━━━━━━━━━━━━━━━━━━━
💙 Ваша трансформация начинается с первого шага!
"""
        
        await update.message.reply_text(consultation_text, parse_mode=ParseMode.MARKDOWN)
    
    async def get_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Получение статистики (только для админов)"""
        user = update.effective_user
        
        # Проверка на админа
        if user.id != 123456789:  # Замените на ваш Telegram ID
            await update.message.reply_text("❌ У вас нет прав для этой команды")
            return
        
        try:
            # Получаем статистику системы
            system_health = self.ai_client.get_system_health()
            
            stats_text = f"""
📊 **СТАТИСТИКА СИСТЕМЫ**

**Токены:**
• Всего запросов: {system_health['token_monitor']['total_requests']}
• Всего токенов: {system_health['token_monitor']['total_tokens']}
• Среднее на запрос: {system_health['token_monitor']['avg_tokens_per_request']:.1f}
• Процент обрезанных: {system_health['token_monitor']['truncation_rate']:.1%}

**Кэш:**
• Записей в кэше: {system_health['response_cache']['total_entries']}
• Процент попаданий: {system_health['response_cache']['hit_rate']:.1%}
• Использование памяти: {system_health['response_cache']['memory_usage_estimate']} байт

**Пользователи:**
• Активных: {system_health['token_monitor']['active_users']}

**Предупреждения:**
{chr(10).join(system_health['token_monitor']['optimization_alerts']) if system_health['token_monitor']['optimization_alerts'] else 'Нет'}
"""
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статистики: {e}")
    
    async def optimize_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Оптимизация для пользователя"""
        user = update.effective_user
        
        try:
            # Получаем статус оптимизации
            optimization_status = self.ai_client.get_user_optimization_status(user.id)
            
            # Применяем оптимизацию
            optimization_result = self.ai_client.optimize_user_experience(user.id)
            
            result_text = f"""
🔧 **ОПТИМИЗАЦИЯ ЗАВЕРШЕНА**

**Примененные оптимизации:**
{chr(10).join([opt['description'] for opt in optimization_result.get('applied_optimizations', [])]) if optimization_result.get('applied_optimizations') else 'Нет автоматических оптимизаций'}

**Рекомендации:**
{chr(10).join([rec.description for rec in optimization_status['optimization_suggestions']]) if optimization_status['optimization_suggestions'] else 'Нет рекомендаций'}

**Статус кэша:**
• Записей: {optimization_status['cache_stats']['total_entries']}
• Попаданий: {optimization_status['cache_stats']['hit_rate']:.1%}
"""
            
            await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка оптимизации: {e}")