#!/usr/bin/env python3
"""
Простая мобильная версия HR-психоаналитического бота
Оптимизирована для быстрой работы на мобильных устройствах
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import openai

# ENV
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Storage
user_data = {}
conversation_history = {}

# Функции базы данных
def init_database():
    conn = sqlite3.connect('simple_mobile_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            message_count INTEGER DEFAULT 0,
            last_analysis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_user_data(telegram_id: int, name: str, message_count: int, analysis: str = None):
    conn = sqlite3.connect('simple_mobile_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (telegram_id, name, message_count, last_analysis, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (telegram_id, name, message_count, analysis, datetime.now()))
    conn.commit()
    conn.close()

def get_user_data(telegram_id: int):
    conn = sqlite3.connect('simple_mobile_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    # Очистка данных
    user_data.pop(user.id, None)
    conversation_history.pop(user.id, None)
    
    welcome_text = """
🤗 **Мобильный HR-Психоаналитик**

Привет! Я ваш персональный помощник.

💙 **Психологическая поддержка**
🧠 **Анализ личности** 
💼 **Карьерные советы**

**Как работаю:**
• Просто общайтесь со мной
• После 10 сообщений проведу анализ
• Оптимизирован для мобильных

**Конфиденциально** 💙
"""
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    
    # Сохранение пользователя
    save_user_data(user.id, user.first_name or f"User_{user.id}", 0)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
💙 **Помощь**

**Команды:**
/start - начать общение
/help - эта справка
/analysis - получить анализ

**Возможности:**
• Психологическая поддержка
• Анализ личности (после 10 сообщений)
• Карьерные рекомендации

**Все конфиденциально!** 💙
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def analysis_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    # Получаем данные пользователя
    user_info = get_user_data(user.id)
    if not user_info:
        await update.message.reply_text("Сначала используйте /start")
        return
    
    message_count = user_info[3]  # message_count
    
    if message_count < 10:
        await update.message.reply_text(
            f"📊 У вас {message_count}/10 сообщений. "
            "Продолжайте общение для получения анализа!"
        )
        return
    
    # Проводим анализ
    thinking_msg = await update.message.reply_text("🤔 Анализирую...")
    
    # Получаем историю разговора
    if user.id in conversation_history:
        conversation_text = " ".join(conversation_history[user.id][-10:])
    else:
        conversation_text = "Недостаточно данных для анализа"
    
    # Простой промпт для анализа
    prompt = f"""
Ты — HR-психоаналитик. Проведи краткий анализ личности.

ДИАЛОГ ({message_count} сообщений):
{conversation_text}

ФОРМАТ ОТВЕТА:
🎯 **КРАТКИЙ ПРОФИЛЬ**

🧠 **Тип личности:** [краткое описание]
💪 **Сильные стороны:** [2-3 качества]
💼 **Подходящие сферы:** [3-4 области]
🎓 **Рекомендации:** [конкретные советы]

СТИЛЬ: Краткий, понятный, мотивирующий. До 200 слов.
"""
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
            timeout=30,
        )
        analysis = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        analysis = "❌ Ошибка при анализе. Попробуйте позже."
    
    await thinking_msg.delete()
    await update.message.reply_text(analysis, parse_mode=ParseMode.MARKDOWN)
    
    # Сохраняем анализ
    save_user_data(user.id, user.first_name or f"User_{user.id}", message_count, analysis)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("Пожалуйста, напишите что-то.")
        return
    
    # Сохранение разговора
    if user.id not in conversation_history:
        conversation_history[user.id] = []
    
    conversation_history[user.id].append(text)
    
    # Ограничение истории
    if len(conversation_history[user.id]) > 15:
        conversation_history[user.id] = conversation_history[user.id][-15:]
    
    # Обновление счетчика сообщений
    user_info = get_user_data(user.id)
    if user_info:
        message_count = user_info[3] + 1
    else:
        message_count = 1
    
    save_user_data(user.id, user.first_name or f"User_{user.id}", message_count)
    
    # Простой ответ
    thinking_msg = await update.message.reply_text("🤔")
    
    # Простой промпт для ответа
    prompt = f"""
Ты — дружелюбный психолог-консультант.

СООБЩЕНИЕ: {text}

ОТВЕТЬ:
- Прояви понимание и эмпатию
- Дай краткий совет (1-2 предложения)
- Задай вопрос для продолжения разговора

СТИЛЬ: Теплый, краткий, поддерживающий. До 100 слов.
"""
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7,
            timeout=20,
        )
        ai_response = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        ai_response = "Понимаю вас. Расскажите больше о вашей ситуации."
    
    await thinking_msg.delete()
    await update.message.reply_text(ai_response)
    
    # Предложение анализа после 10 сообщений
    if message_count == 10:
        await update.message.reply_text(
            "🎯 У вас уже 10 сообщений! Используйте /analysis для получения анализа личности."
        )

def main():
    # Инициализация базы данных
    init_database()
    
    # Создание приложения
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('analysis', analysis_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Простой мобильный HR-психоаналитик запущен")
    application.run_polling()

if __name__ == "__main__":
    main()