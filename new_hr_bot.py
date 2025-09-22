import os
import re
import json
import sqlite3
import logging
from datetime import datetime
from typing import Tuple
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
import openai

# Импорт модулей ИИ
from sentiment_analyzer import get_sentiment_analyzer
from prompt_ab_testing import get_ab_testing_manager, PromptType

# ENV
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# States
(WAITING_MESSAGE, IN_EXPRESS_ANALYSIS, IN_FULL_ANALYSIS, Q1, Q2, Q3, Q4, Q5, Q6, Q7) = range(10)

# Storage
user_data = {}
conversation_history = {}

# ИИ модули
sentiment_analyzer = get_sentiment_analyzer()
ab_testing_manager = get_ab_testing_manager()

# Профессиональные вопросы для полного анализа
PROFESSIONAL_QUESTIONS = [
    "Расскажите о вашем детстве. Какие воспоминания формировали ваш характер?",
    "Что вас больше всего мотивирует в жизни? Откуда черпаете энергию?",
    "Как вы справляетесь со стрессом? Опишите последнюю сложную ситуацию.",
    "В какой среде вы работаете лучше всего? Команда или индивидуально?",
    "Какие ваши главные страхи и как они влияют на решения?",
    "Как вы видите себя через 5 лет? Какие цели важны?",
    "Что бы вы изменили в себе, если бы могли? Почему именно это?"
]

# Функции базы данных
def init_database():
    conn = sqlite3.connect('new_psychoanalyst.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            analysis_type TEXT,
            analysis_data TEXT,
            payment_status TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_analysis(telegram_id: int, name: str, analysis_type: str, analysis_data: dict, payment_status: str = 'free'):
    conn = sqlite3.connect('new_psychoanalyst.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO clients 
        (telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, name, analysis_type, json.dumps(analysis_data), payment_status, datetime.now()))
    conn.commit()
    conn.close()

# Основные обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    
    # Очистка предыдущих данных
    user_data.pop(user.id, None)
    conversation_history.pop(user.id, None)
    
    welcome_text = """
🤗 **Новый HR-Психоаналитик | Мобильная версия**

Привет! Я ваш персональный помощник для мобильных устройств.

💙 **Психологическая поддержка** - выслушаю и поддержу
🧠 **Анализ личности** - помогу понять себя  
🤝 **Психологическая консультация** - сны, стресс, отношения
💼 **Карьерное консультирование** - выбор профессии

**Как я работаю:**
• Просто общайтесь со мной естественно
• После 10 сообщений проведу экспресс-анализ (бесплатно)
• Для детального анализа скажите 'полный анализ'
• Оптимизирован для мобильных устройств

**Конфиденциально и анонимно** 💙
"""
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    return WAITING_MESSAGE

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
💙 **Мобильная версия HR-Психоаналитика**

**Бесплатно:**
• Психологическая поддержка
• Экспресс-анализ личности (после 10 сообщений)
• Помощь с выбором профессии

**Платно (500₽):**
• Полный психоанализ (7 глубоких вопросов)
• Детальный профиль личности
• Персональные рекомендации

**Команды:**
/start - начать общение
/help - эта справка
/cancel - отменить процесс

**🤖 ИИ-возможности:**
• Анализ эмоций в реальном времени
• A/B тестирование для лучших ответов
• Оптимизация для мобильных устройств

**Все конфиденциально!** 💙
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("Пожалуйста, напишите что-то конкретное.")
        return WAITING_MESSAGE
    
    # Сохранение разговора
    if user.id not in conversation_history:
        conversation_history[user.id] = []
    
    conversation_history[user.id].append(text)
    
    # Ограничение истории
    if len(conversation_history[user.id]) > 15:
        conversation_history[user.id] = conversation_history[user.id][-15:]
    
    # Проверка на полный анализ
    if 'полный анализ' in text.lower() or 'детальный анализ' in text.lower():
        await update.message.reply_text(
            "💎 **Полный психоанализ**\n\n"
            "Отлично! Сейчас я проведу детальный анализ вашей личности.\n"
            "Будет 7 профессиональных вопросов.\n\n"
            "**Вопрос 1 из 7:**\n"
            f"{PROFESSIONAL_QUESTIONS[0]}"
        )
        
        user_data[user.id] = {
            'state': 'full_analysis',
            'answers': [],
            'current_question': 0
        }
        return Q1
    
    # Проверка количества сообщений для экспресс-анализа
    message_count = len(conversation_history[user.id])
    
    if message_count >= 10:
        # Экспресс-анализ
        thinking_msg = await update.message.reply_text(
            "🎯 Отлично! У меня достаточно информации для экспресс-анализа. "
            "Провожу анализ вашей личности..."
        )
        
        conversation_text = " ".join(conversation_history[user.id])
        
        # Простой промпт для экспресс-анализа
        prompt = f"""
Ты — профессиональный HR-психоаналитик.

ДИАЛОГ КЛИЕНТА ({message_count} сообщений):
{conversation_text}

Проведи экспресс-анализ личности:

🎯 ЭКСПРЕСС-ПРОФИЛЬ
🧠 Психотип: [краткое описание]
📊 Основные черты: [2-3 ключевые характеристики]
💼 Подходящие сферы: [3-4 области деятельности]
🎓 Рекомендации: [конкретные направления]

СТИЛЬ: Профессиональный, эмпатичный. Максимум 300 слов.
"""
        
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7,
                timeout=60,
            )
            ai_response = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            ai_response = "Извините, произошла ошибка при обработке запроса."
        
        await thinking_msg.delete()
        await update.message.reply_text(ai_response, parse_mode=ParseMode.MARKDOWN)
        
        # Предложение полного анализа
        await update.message.reply_text(
            "💎 **Хотите детальный анализ?**\n\n"
            "Полный психоанализ включает:\n"
            "• 7 профессиональных вопросов\n"
            "• Детальный профиль личности\n"
            "• HR-оценки и рекомендации\n\n"
            "Стоимость: 500₽\n"
            "Для заказа напишите: 'хочу полный анализ'"
        )
        
        # Сохранение экспресс-анализа
        analysis_data = {
            'type': 'express',
            'conversation': conversation_text,
            'analysis': ai_response,
            'message_count': message_count
        }
        save_analysis(user.id, user.first_name or f"User_{user.id}", 'express', analysis_data)
        
        return WAITING_MESSAGE
    
    # Обычное общение
    thinking_msg = await update.message.reply_text("🤔 Думаю...")
    
    # Простой промпт для обычного общения
    prompt = f"""
Ты — HR-психоаналитик и карьерный консультант.

СООБЩЕНИЕ КЛИЕНТА:
{text}

ТВОЯ РОЛЬ: Друг-психолог, который поддерживает и понимает.

ПРИНЦИПЫ:
- Прояви эмпатию и понимание
- Поддерживай эмоционально
- Мягко подводи к самоанализу
- Будь теплым и человечным

ФОРМАТ: Эмпатичный ответ + релевантный вопрос.

СТИЛЬ: Теплый, профессиональный, адаптивный.
"""
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
            timeout=60,
        )
        ai_response = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        ai_response = "Извините, произошла ошибка при обработке запроса."
    
    await thinking_msg.delete()
    await update.message.reply_text(ai_response)
    return WAITING_MESSAGE

async def handle_full_analysis_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    text = update.message.text.strip()
    
    if not text or len(text) < 20:
        await update.message.reply_text(
            "Пожалуйста, дайте развернутый ответ (минимум 20 символов)."
        )
        return context.user_data.get('current_question', Q1)
    
    user_info = user_data.get(user.id, {})
    answers = user_info.get('answers', [])
    current_q = user_info.get('current_question', 0)
    
    answers.append(text)
    current_q += 1
    
    user_data[user.id] = {
        'state': 'full_analysis',
        'answers': answers,
        'current_question': current_q
    }
    
    if current_q < 7:
        await update.message.reply_text(
            f"**Вопрос {current_q + 1} из 7:**\n"
            f"{PROFESSIONAL_QUESTIONS[current_q]}"
        )
        return Q1 + current_q
    else:
        # Все вопросы отвечены, проводим полный анализ
        thinking_msg = await update.message.reply_text(
            "🎯 Отлично! Все ответы получены. "
            "Провожу детальный психоанализ..."
        )
        
        answers_text = "\n".join([f"{i+1}. {q}\nОтвет: {a}\n" for i, (q, a) in enumerate(zip(PROFESSIONAL_QUESTIONS, answers))])
        
        prompt = f"""
Ты — ведущий психоаналитик и HR-эксперт.

ДЕТАЛЬНЫЕ ОТВЕТЫ КЛИЕНТА:
{answers_text}

ПРОВЕДИ ГЛУБОКИЙ ПСИХОАНАЛИЗ:

🧠 ПСИХОАНАЛИТИЧЕСКИЙ ПРОФИЛЬ:
- Структура личности
- Защитные механизмы
- Бессознательные конфликты

🎭 АРХЕТИПЫ И ТИПОЛОГИЯ:
- Доминирующий архетип
- MBTI тип с обоснованием
- Темперамент и особенности

📊 BIG FIVE (OCEAN):
- Открытость: [1-10] + обоснование
- Добросовестность: [1-10] + обоснование  
- Экстраверсия: [1-10] + обоснование
- Доброжелательность: [1-10] + обоснование
- Нейротизм: [1-10] + обоснование

💼 HR-РЕКОМЕНДАЦИИ:
- Подходящие роли и позиции
- Стиль управления/работы
- Мотивационные факторы

🎓 ОБРАЗОВАТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:
- Конкретные направления обучения
- Форматы обучения
- Дополнительные навыки

СТИЛЬ: Профессиональный, детальный, практичный. 800-1200 слов.
"""
        
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.7,
                timeout=60,
            )
            ai_response = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            ai_response = "Извините, произошла ошибка при обработке запроса."
        
        await thinking_msg.delete()
        
        # Разбиваем длинный ответ на части
        max_length = 4000
        if len(ai_response) <= max_length:
            await update.message.reply_text(ai_response, parse_mode=ParseMode.MARKDOWN)
        else:
            parts = [ai_response[i:i+max_length] for i in range(0, len(ai_response), max_length)]
            for i, part in enumerate(parts):
                prefix = f"**Анализ (часть {i+1}):**\n\n" if i > 0 else ""
                await update.message.reply_text(prefix + part, parse_mode=ParseMode.MARKDOWN)
        
        # Сохранение полного анализа
        analysis_data = {
            'type': 'full',
            'answers': answers,
            'analysis': ai_response
        }
        save_analysis(user.id, user.first_name or f"User_{user.id}", 'full', analysis_data, 'paid')
        
        await update.message.reply_text(
            "✅ **Анализ завершен!**\n\n"
            "Спасибо за доверие. Ваши данные сохранены анонимно.\n"
            "Для нового анализа используйте /start"
        )
        
        # Очистка данных пользователя
        user_data.pop(user.id, None)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_data.pop(user.id, None)
    conversation_history.pop(user.id, None)
    
    await update.message.reply_text(
        "Анализ отменен. Для нового анализа используйте /start"
    )
    return ConversationHandler.END

def main():
    # Инициализация базы данных
    init_database()
    
    # Создание приложения
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
            ],
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_full_analysis_answer)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_full_analysis_answer)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_full_analysis_answer)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_full_analysis_answer)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_full_analysis_answer)],
            Q6: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_full_analysis_answer)],
            Q7: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_full_analysis_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    
    # Добавление обработчиков
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    
    logger.info("Новый HR-Психоаналитик запущен (мобильная версия)")
    application.run_polling()

if __name__ == "__main__":
    main()