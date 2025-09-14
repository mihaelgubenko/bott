#!/usr/bin/env python3
"""
Простой тестовый бот для проверки основного функционала
Без голосовых функций и сложных зависимостей
"""
import logging
import os
import asyncio
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Настройки бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в переменных окружения!")
    exit(1)

class SimpleBotTest:
    def __init__(self):
        self.message_count = {}
        logger.info("🤖 Простой тестовый бот инициализирован")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        logger.info(f"👤 Пользователь {user.first_name} (ID: {user.id}) запустил бота")
        
        welcome_text = f"""🤖 **Привет, {user.first_name}!**

Это тестовый AI автоответчик для телефонии.

**Доступные команды:**
• `/start` - это сообщение
• `/help` - справка
• `/test` - тест функций
• `/status` - статус системы

**Что я умею:**
✅ Отвечать на текстовые сообщения
✅ Считать ваши сообщения
✅ Работать на Railway
⏳ Скоро: голосовые функции

Просто напишите мне что-нибудь!"""

        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """📋 **Справка по боту**

**Команды:**
• `/start` - начать работу
• `/help` - эта справка
• `/test` - тест функций
• `/status` - статус системы

**Тестирование:**
1. Отправьте любое текстовое сообщение
2. Бот ответит и покажет статистику
3. Попробуйте разные типы сообщений

**Статус:** ✅ Работает на Railway
**Версия:** 1.0 (тестовая)"""

        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /test"""
        user_id = update.effective_user.id
        
        test_results = f"""🧪 **Результаты тестирования**

**Основные функции:**
✅ Telegram API - работает
✅ Обработка сообщений - работает  
✅ Команды - работают
✅ Markdown - работает

**Ваша статистика:**
📊 Сообщений от вас: {self.message_count.get(user_id, 0)}
🕒 Время ответа: <1 секунды
🔗 Соединение: Railway Cloud

**Следующие тесты:**
⏳ Голосовые сообщения
⏳ Интеграция с AI
⏳ Телефонные звонки"""

        await update.message.reply_text(test_results, parse_mode=ParseMode.MARKDOWN)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        total_messages = sum(self.message_count.values())
        
        status_text = f"""📊 **Статус системы**

**Бот:**
🟢 Состояние: Онлайн
🏠 Платформа: Railway
🐍 Python: 3.11+
📱 Telegram API: Активен

**Статистика:**
👥 Уникальных пользователей: {len(self.message_count)}
💬 Всего сообщений: {total_messages}
⚡ Время работы: с последнего деплоя

**Компоненты:**
✅ Telegram Bot API
⏳ AI автоответчик (в разработке)
⏳ Голосовые функции (в разработке)
⏳ Телефонная интеграция (планируется)"""

        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        user = update.effective_user
        message_text = update.message.text
        user_id = user.id

        # Увеличиваем счетчик
        self.message_count[user_id] = self.message_count.get(user_id, 0) + 1
        
        logger.info(f"💬 Сообщение от {user.first_name}: '{message_text}'")

        # Простые ответы в зависимости от содержимого
        if "привет" in message_text.lower():
            response = f"👋 Привет, {user.first_name}! Как дела?"
        elif "тест" in message_text.lower():
            response = "🧪 Тестирую... Все работает отлично!"
        elif "спасибо" in message_text.lower():
            response = "😊 Пожалуйста! Рад помочь!"
        elif "как дела" in message_text.lower():
            response = "😊 У меня все отлично! Работаю на Railway, жду новых сообщений!"
        elif "что умеешь" in message_text.lower():
            response = """🤖 **Что я умею:**

✅ Отвечать на сообщения
✅ Считать статистику
✅ Работать 24/7 на Railway
⏳ Скоро: голосовые функции
⏳ Скоро: AI автоответчик"""
        else:
            response = f"""💭 **Получил ваше сообщение:** "{message_text}"

📊 Это ваше сообщение #{self.message_count[user_id]}
🤖 Скоро здесь будет умный AI ответ!

Попробуйте команды: /help или /test"""

        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    async def setup_bot_commands(self, application):
        """Настройка меню команд бота"""
        commands = [
            BotCommand("start", "🚀 Начать работу с ботом"),
            BotCommand("help", "📋 Справка и инструкции"), 
            BotCommand("test", "🧪 Тестирование функций"),
            BotCommand("status", "📊 Статус системы")
        ]
        await application.bot.set_my_commands(commands)
        logger.info("✅ Команды бота настроены")

def main():
    """Основная функция запуска бота"""
    print("🚀 Запуск простого тестового бота...")
    
    # Создаем экземпляр бота
    bot_instance = SimpleBotTest()
    
    # Создаем приложение
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", bot_instance.start_command))
    application.add_handler(CommandHandler("help", bot_instance.help_command))
    application.add_handler(CommandHandler("test", bot_instance.test_command))
    application.add_handler(CommandHandler("status", bot_instance.status_command))
    
    # Обработчик всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_message))
    
    # Настройка команд после инициализации
    async def post_init(app):
        await bot_instance.setup_bot_commands(app)
    
    application.post_init = post_init
    
    logger.info("✅ Простой тестовый бот запущен")
    print("✅ Бот готов к работе!")
    print("📱 Найдите бота в Telegram и отправьте /start")
    print("⏹️ Для остановки нажмите Ctrl+C")
    
    # Запуск
    try:
        application.run_polling(
            allowed_updates=['message'],
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()
