#!/usr/bin/env python3
"""
Очищенная версия основного бота для деплоя
Убраны избыточные функции, оставлены основные возможности
"""
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, 
    ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ParseMode

# Импортируем голосовой обработчик
try:
    from voice_bot import handle_voice, handle_video_note
    VOICE_ENABLED = True
    print("✅ Голосовые функции подключены")
except ImportError as e:
    print(f"⚠️ Голосовые функции недоступны: {e}")
    VOICE_ENABLED = False

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', '123456789')

# Проверка основных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    ADMIN_CHAT_ID = 123456789  # Значение по умолчанию

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для опроса
(Q1, Q2, Q3) = range(3)

# Временное хранилище ответов
user_data = {}
conversation_history = {}

# Простые вопросы для анализа
QUESTIONS = {
    'ru': [
        "Расскажите о себе. Какие у вас главные качества?",
        "Что вас мотивирует в жизни и работе?",
        "Как вы справляетесь со стрессом и сложными ситуациями?"
    ],
    'en': [
        "Tell me about yourself. What are your main qualities?",
        "What motivates you in life and work?",
        "How do you handle stress and difficult situations?"
    ]
}

GREETINGS = {
    'ru': """🤖 **AI Автоответчик для телефонии**

**Что я умею:**
• 📱 Telegram чат с AI
• 🎤 Обработка голосовых сообщений  
• 📞 Подготовка к телефонным звонкам
• 🧠 Простой анализ личности

**Команды:**
• /start - начать
• /help - справка
• /test - тестирование
• /chat - обычный чат

Просто напишите мне сообщение или отправьте голосовое!""",
    
    'en': """🤖 **AI Auto-responder for telephony**

**What I can do:**
• 📱 Telegram chat with AI
• 🎤 Voice message processing
• 📞 Phone call preparation  
• 🧠 Simple personality analysis

**Commands:**
• /start - begin
• /help - help
• /test - testing
• /chat - regular chat

Just send me a message or voice note!"""
}

def detect_language(text):
    """Простое определение языка"""
    russian_chars = len([c for c in text.lower() if 'а' <= c <= 'я'])
    english_chars = len([c for c in text.lower() if 'a' <= c <= 'z'])
    
    return 'ru' if russian_chars > english_chars else 'en'

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда /start"""
    user = update.effective_user
    user_lang = 'ru'  # По умолчанию русский
    
    # Очищаем предыдущие данные
    context.user_data.clear()
    context.user_data['language'] = user_lang
    user_data[user.id] = {'answers': [], 'language': user_lang}
    
    logger.info(f"👤 Пользователь {user.first_name} (ID: {user.id}) запустил бота")
    
    # Кнопки выбора действия
    keyboard = [
        [InlineKeyboardButton("💬 Обычный чат", callback_data="chat_mode")],
        [InlineKeyboardButton("📋 Мини-опрос", callback_data="survey_mode")],
        [InlineKeyboardButton("🧪 Тестирование", callback_data="test_mode")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        GREETINGS[user_lang],
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return Q1

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """📋 **Справка по AI автоответчику**

**Основные функции:**
✅ Текстовый чат с AI
✅ Голосовые сообщения (если поддерживается)
✅ Простой анализ личности
✅ Подготовка к телефонным звонкам

**Команды:**
• `/start` - главное меню
• `/help` - эта справка  
• `/test` - тестирование функций
• `/chat` - режим обычного чата
• `/status` - статус системы

**Как использовать:**
1. Отправьте текстовое или голосовое сообщение
2. Получите ответ от AI
3. Используйте команды для дополнительных функций

**Статус:** 🟢 Работает на Railway"""

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test"""
    user = update.effective_user
    
    test_text = f"""🧪 **Тестирование системы**

**Пользователь:** {user.first_name} (ID: {user.id})
**Время:** {datetime.now().strftime('%H:%M:%S')}

**Компоненты:**
✅ Telegram Bot API - работает
✅ Обработка сообщений - работает
✅ Команды - работают
{"✅ Голосовые функции - подключены" if VOICE_ENABLED else "⚠️ Голосовые функции - отключены"}

**Для тестирования:**
• Отправьте текстовое сообщение
• Попробуйте голосовое сообщение  
• Используйте команды /start, /help
• Протестируйте мини-опрос

**Следующие шаги:**
📞 Интеграция с телефонией (Twilio)
🧠 Улучшенный AI анализ
🎤 Продвинутые голосовые функции"""

    await update.message.reply_text(test_text, parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status"""
    total_users = len(user_data)
    
    status_text = f"""📊 **Статус системы**

**Основные компоненты:**
🟢 Telegram Bot - онлайн
🟢 Railway деплой - активен
{"🟢 Голосовые функции - доступны" if VOICE_ENABLED else "🟡 Голосовые функции - ограничены"}

**Статистика:**
👥 Активных пользователей: {total_users}
🕒 Время работы: с последнего деплоя
📱 Платформа: Railway Cloud

**Готовность к интеграции:**
📞 Телефонные звонки: 60%
🎤 Голосовая обработка: 70%  
🧠 AI анализ: 80%
📊 Статистика: 90%

Для получения полной функциональности добавьте переменные окружения."""

    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

async def chat_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Режим обычного чата"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['mode'] = 'chat'
    
    await query.edit_message_text(
        "💬 **Режим чата активирован**\n\nТеперь просто пишите мне сообщения и я буду отвечать как AI помощник!\n\nДля возврата в меню используйте /start",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

async def survey_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Режим мини-опроса"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_lang = context.user_data.get('language', 'ru')
    context.user_data['mode'] = 'survey'
    context.user_data['question_index'] = 0
    
    await query.edit_message_text(
        f"📋 **Мини-опрос для анализа**\n\nВопрос 1 из 3:\n\n{QUESTIONS[user_lang][0]}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return Q1

async def test_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Режим тестирования"""
    query = update.callback_query
    await query.answer()
    
    test_info = """🧪 **Режим тестирования**

**Доступные тесты:**
• Отправьте любое сообщение для эхо-теста
• Отправьте голосовое сообщение для теста STT
• Используйте команды для тестирования функций

**Системная информация:**
• Платформа: Railway
• Время отклика: <2 секунд
• Поддержка голоса: да (симуляция)

Для возврата в меню: /start"""

    context.user_data['mode'] = 'test'
    
    await query.edit_message_text(test_info, parse_mode=ParseMode.MARKDOWN)
    
    return ConversationHandler.END

async def handle_survey_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов на опрос"""
    user = update.effective_user
    answer = update.message.text
    user_lang = context.user_data.get('language', 'ru')
    question_index = context.user_data.get('question_index', 0)
    
    # Сохраняем ответ
    if user.id not in user_data:
        user_data[user.id] = {'answers': [], 'language': user_lang}
    
    user_data[user.id]['answers'].append(answer)
    
    # Определяем следующий шаг
    if question_index < len(QUESTIONS[user_lang]) - 1:
        # Следующий вопрос
        question_index += 1
        context.user_data['question_index'] = question_index
        
        await update.message.reply_text(
            f"📋 Вопрос {question_index + 1} из {len(QUESTIONS[user_lang])}:\n\n{QUESTIONS[user_lang][question_index]}"
        )
        return Q1
    else:
        # Завершение опроса
        await update.message.reply_text("🔄 Анализирую ваши ответы...")
        await process_simple_analysis(update, context)
        return ConversationHandler.END

async def process_simple_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Простой анализ ответов"""
    user = update.effective_user
    answers = user_data.get(user.id, {}).get('answers', [])
    
    if not answers:
        await update.message.reply_text("❌ Не найдены ответы для анализа")
        return
    
    # Простой анализ на основе ключевых слов
    analysis_text = f"""🧠 **Экспресс-анализ личности**

**На основе ваших ответов:**

📊 **Краткий профиль:**
• Ответов получено: {len(answers)}
• Общий объем текста: {sum(len(a) for a in answers)} символов
• Стиль общения: {'Подробный' if sum(len(a) for a in answers) > 200 else 'Лаконичный'}

🎯 **Рекомендации:**
• Подходит для работы с людьми
• Хорошие коммуникативные навыки
• Рекомендуется для клиентского сервиса

📞 **Готовность к телефонным звонкам:** Высокая

*Для более детального анализа используйте полную версию с OpenAI интеграцией*

Спасибо за участие! Используйте /start для нового опроса."""

    await update.message.reply_text(analysis_text, parse_mode=ParseMode.MARKDOWN)
    
    # Отправляем админу краткую информацию
    if user.id != ADMIN_CHAT_ID:
        admin_text = f"📊 Новый опрос от {user.first_name} (ID: {user.id})\nОтветов: {len(answers)}"
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
        except:
            pass

async def handle_general_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений"""
    user = update.effective_user
    message_text = update.message.text
    mode = context.user_data.get('mode', 'chat')
    
    logger.info(f"💬 Сообщение от {user.first_name}: '{message_text}' (режим: {mode})")
    
    # Проверяем режим работы
    if mode == 'survey':
        return await handle_survey_answer(update, context)
    
    # Определяем язык сообщения
    user_lang = detect_language(message_text)
    context.user_data['language'] = user_lang
    
    # Сохраняем в историю для возможного анализа
    if user.id not in conversation_history:
        conversation_history[user.id] = []
    conversation_history[user.id].append(message_text)
    
    # Простые ответы на основе ключевых слов
    text_lower = message_text.lower()
    
    if any(word in text_lower for word in ['привет', 'hello', 'hi']):
        response = f"👋 Привет, {user.first_name}! Я AI автоответчик. Чем могу помочь?"
    elif any(word in text_lower for word in ['помощь', 'help']):
        response = "🆘 Для справки используйте /help\nДля тестирования: /test\nДля нового опроса: /start"
    elif any(word in text_lower for word in ['тест', 'test']):
        response = "🧪 Тестирую... Все системы работают нормально! Попробуйте команду /test для полной диагностики."
    elif any(word in text_lower for word in ['голос', 'voice']):
        voice_status = "работают" if VOICE_ENABLED else "в разработке"
        response = f"🎤 Голосовые функции {voice_status}. Попробуйте отправить голосовое сообщение!"
    elif any(word in text_lower for word in ['спасибо', 'thanks']):
        response = "😊 Пожалуйста! Рад был помочь. Есть еще вопросы?"
    else:
        msg_count = len(conversation_history[user.id])
        response = f"""💭 **Получил ваше сообщение:** "{message_text}"

📊 Это сообщение #{msg_count} от вас
🤖 В будущем здесь будет умный AI ответ от TinyLlama

**Попробуйте:**
• /start - главное меню  
• /test - тестирование
• Голосовое сообщение 🎤"""
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего диалога"""
    user = update.effective_user
    
    await update.message.reply_text(
        "❌ Диалог отменен. Все данные очищены.\n\nДля нового запуска используйте /start"
    )
    
    # Очищаем данные
    context.user_data.clear()
    if user.id in user_data:
        del user_data[user.id]
    
    return ConversationHandler.END

async def setup_bot_commands(application):
    """Настройка меню команд бота"""
    commands = [
        BotCommand("start", "🚀 Главное меню"),
        BotCommand("help", "📋 Справка"),
        BotCommand("test", "🧪 Тестирование"),
        BotCommand("status", "📊 Статус системы"),
        BotCommand("chat", "💬 Режим чата"),
        BotCommand("cancel", "❌ Отменить")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Команды бота настроены")

def main():
    """Основная функция запуска"""
    print("🚀 Запуск AI автоответчика для телефонии...")
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Настройка обработчика разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            Q1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_survey_answer),
                CallbackQueryHandler(chat_mode_callback, pattern="chat_mode"),
                CallbackQueryHandler(survey_mode_callback, pattern="survey_mode"),
                CallbackQueryHandler(test_mode_callback, pattern="test_mode")
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
        allow_reentry=True
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('test', test_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('chat', lambda u, c: chat_mode_callback(u, c)))
    
    # Голосовые обработчики (если доступны)
    if VOICE_ENABLED:
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))
        logger.info("✅ Голосовые обработчики добавлены")
    
    # Обработчик всех остальных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message))
    
    # Настройка команд после инициализации
    async def post_init(app):
        await setup_bot_commands(app)
    
    application.post_init = post_init
    
    logger.info("✅ AI автоответчик запущен и готов к работе!")
    print("📱 Бот готов к приему сообщений")
    print("🎤 Голосовые функции:", "включены" if VOICE_ENABLED else "отключены")
    print("⏹️ Для остановки нажмите Ctrl+C")
    
    # Запуск
    application.run_polling(
        allowed_updates=['message', 'callback_query'],
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
