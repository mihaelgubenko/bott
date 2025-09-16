import os
import re
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
    ConversationHandler,
    filters,
)
import openai

# ENV
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")  # Для оплаты

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

# Professional 7 questions for full analysis
PROFESSIONAL_QUESTIONS = [
    "Расскажите о вашем детстве. Какие воспоминания формировали ваш характер?",
    "Что вас больше всего мотивирует в жизни? Откуда черпаете энергию?",
    "Как вы справляетесь со стрессом? Опишите последнюю сложную ситуацию.",
    "В какой среде вы работаете лучше всего? Команда или индивидуально?",
    "Какие ваши главные страхи и как они влияют на решения?",
    "Как вы видите себя через 5 лет? Какие цели важны?",
    "Что бы вы изменили в себе, если бы могли? Почему именно это?"
]

# Database functions
def init_database():
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            analysis_type TEXT,  -- 'express' or 'full'
            analysis_data TEXT,  -- JSON
            payment_status TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_analysis(telegram_id: int, name: str, analysis_type: str, analysis_data: dict, payment_status: str = 'free'):
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO clients 
        (telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, name, analysis_type, json.dumps(analysis_data), payment_status, datetime.now()))
    conn.commit()
    conn.close()

def get_user_analyses(telegram_id: int):
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients WHERE telegram_id = ? ORDER BY created_at DESC', (telegram_id,))
    analyses = cursor.fetchall()
    conn.close()
    return analyses

# Language detection
def detect_language(text: str) -> str:
    if not text or text.strip() in ['/start', '/help', '/cancel']:
        return 'ru'
    
    text = text.strip()
    
    # Проверяем наличие кириллицы
    if any('\u0400' <= char <= '\u04FF' for char in text):
        return 'ru'
    
    # По умолчанию русский
    return 'ru'

# Professional prompts
def get_express_analysis_prompt(conversation: str, message_count: int) -> str:
    return f"""
Ты — профессиональный HR-психоаналитик и карьерный консультант. 

ДИАЛОГ КЛИЕНТА ({message_count} сообщений):
{conversation}

ЗАДАЧА: Проведи экспресс-анализ личности на основе диалога.

МЕТОДОЛОГИЯ:
- Психоанализ (Фрейд): защитные механизмы, бессознательные мотивы
- Аналитическая психология (Юнг): архетипы, типы личности
- MBTI: предпочтения в восприятии и принятии решений
- Big Five: основные черты личности

ФОРМАТ ОТВЕТА:
🎯 ЭКСПРЕСС-ПРОФИЛЬ

🧠 Психотип: [краткое описание на основе Юнга/Фрейда]
📊 Основные черты: [2-3 ключевые характеристики]
💼 Подходящие сферы: [3-4 области деятельности]
🎓 Рекомендации по обучению: [конкретные направления]
⚠️ Зоны развития: [что стоит развивать]

СТИЛЬ: Профессиональный, эмпатичный, конкретный. Максимум 300 слов.
"""

def get_full_analysis_prompt(answers: list) -> str:
    answers_text = "\n".join([f"{i+1}. {q}\nОтвет: {a}\n" for i, (q, a) in enumerate(zip(PROFESSIONAL_QUESTIONS, answers))])
    
    return f"""
Ты — ведущий психоаналитик и HR-эксперт с 20-летним опытом.

ДЕТАЛЬНЫЕ ОТВЕТЫ КЛИЕНТА:
{answers_text}

ПРОВЕДИ ГЛУБОКИЙ ПСИХОАНАЛИЗ:

🧠 ПСИХОАНАЛИТИЧЕСКИЙ ПРОФИЛЬ:
- Структура личности (Ид/Эго/Суперэго)
- Защитные механизмы
- Бессознательные конфликты
- Травмы и их влияние

🎭 АРХЕТИПЫ И ТИПОЛОГИЯ:
- Доминирующий архетип по Юнгу
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
- Потенциальные риски

🎓 ОБРАЗОВАТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:
- Конкретные направления обучения
- Форматы обучения (очное/заочное)
- Дополнительные навыки
- Карьерная траектория

🔮 ПРОГНОЗ РАЗВИТИЯ:
- Как будет развиваться личность
- Ключевые точки роста
- Рекомендации по саморазвитию

СТИЛЬ: Профессиональный, детальный, практичный. 800-1200 слов.
"""

def get_psychology_consultation_prompt(user_message: str) -> str:
    return f"""
Ты — опытный психолог с большим сердцем. Твоя главная задача - ПОДДЕРЖАТЬ и ПОНИМАТЬ.

СООБЩЕНИЕ КЛИЕНТА:
{user_message}

ТВОЯ РОЛЬ: Друг-психолог, который всегда на стороне человека.

ПРИНЦИПЫ:
- СНАЧАЛА прояви эмпатию и понимание
- НЕ давай советы, если человек не просит
- Поддерживай эмоционально
- Будь теплым и человечным

ФОРМАТ ОТВЕТА:
💙 Эмпатичный ответ (понимание чувств)
🤗 Поддержка и принятие
💡 Мягкие рекомендации (если уместно)

СТИЛЬ: Теплый, понимающий, как разговор с близким другом. 150-300 слов.
"""

# OpenAI client
async def get_ai_response(prompt: str, max_tokens: int = 1000) -> str:
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
            timeout=60,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Извините, произошла ошибка при обработке запроса. Попробуйте позже."

# Main handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    
    # Clear previous data
    user_data.pop(user.id, None)
    conversation_history.pop(user.id, None)
    
    welcome_text = """
🤗 **Психолог-консультант | Ваш помощник**

Привет! Я ваш персональный психолог-консультант. Я здесь, чтобы:

💙 **Поддержать вас в трудную минуту**
🧠 **Помочь разобраться в себе и чувствах**
🤝 **Дать психологическую консультацию**
💼 **При необходимости помочь с карьерой**

**Как я работаю:**
• Просто поговорите со мной - я выслушаю и поддержу
• После 10 сообщений предложу экспресс-анализ (бесплатно)
• Для детального психоанализа скажите 'полный анализ'

**Конфиденциально и анонимно** 💙

Расскажите, как дела? Что вас беспокоит или радует?
"""
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    return WAITING_MESSAGE

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
💙 **Я здесь, чтобы помочь:**

**Бесплатно:**
• Психологическая поддержка и консультация
• Экспресс-анализ личности (после 10 сообщений)
• Помощь с выбором профессии

**Платно (500₽):**
• Полный психоанализ (7 глубоких вопросов)
• Детальный профиль личности
• Персональные рекомендации по развитию

**Команды:**
/start - начать общение
/help - эта справка
/cancel - отменить текущий процесс

**Все конфиденциально и анонимно!** 💙
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_data.pop(user.id, None)
    conversation_history.pop(user.id, None)
    
    await update.message.reply_text(
        "Анализ отменен. Для нового анализа используйте /start"
    )
    return ConversationHandler.END

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очистить память бота (только для админов)"""
    user = update.effective_user
    
    # Проверка на админа (можно настроить)
    if user.id != 123456789:  # Замените на ваш Telegram ID
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    # Очистка памяти
    user_data.clear()
    conversation_history.clear()
    
    # Очистка базы данных
    try:
        conn = sqlite3.connect('psychoanalyst.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clients')
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            "✅ Память бота полностью очищена:\n"
            "• Очищена RAM память\n"
            "• Очищена база данных\n"
            "• Все диалоги удалены"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при очистке: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("Пожалуйста, напишите что-то конкретное.")
        return WAITING_MESSAGE
    
    # Detect language
    language = detect_language(text)
    if language != 'ru':
        await update.message.reply_text("Я работаю только на русском языке. Пожалуйста, напишите на русском.")
        return WAITING_MESSAGE
    
    # Store conversation
    if user.id not in conversation_history:
        conversation_history[user.id] = []
    
    conversation_history[user.id].append(text)
    
    # Keep only last 15 messages
    if len(conversation_history[user.id]) > 15:
        conversation_history[user.id] = conversation_history[user.id][-15:]
    
    # Check for full analysis request
    if 'полный анализ' in text.lower() or 'детальный анализ' in text.lower() or 'платный анализ' in text.lower():
        # Check if user already has full analysis
        analyses = get_user_analyses(user.id)
        has_full_analysis = any(analysis[3] == 'full' for analysis in analyses)
        
        if has_full_analysis:
            await update.message.reply_text(
                "У вас уже есть полный анализ! Для нового анализа используйте /start"
            )
            return WAITING_MESSAGE
        
        # Start full analysis
        user_data[user.id] = {
            'state': 'full_analysis',
            'answers': [],
            'current_question': 0
        }
        
        await update.message.reply_text(
            "💎 **Полный психоанализ**\n\n"
            "Отлично! Сейчас я проведу детальный анализ вашей личности.\n"
            "Будет 7 профессиональных вопросов.\n\n"
            "**Вопрос 1 из 7:**\n"
            f"{PROFESSIONAL_QUESTIONS[0]}"
        )
        
        return Q1
    
    # Check if it's a psychology-related question
    psychology_keywords = ['сон', 'сны', 'депрессия', 'тревога', 'стресс', 'паника', 'страх', 'грусть', 'одиночество', 'отношения', 'семья', 'родители', 'дети', 'любовь', 'развод', 'смерть', 'потеря']
    
    if any(keyword in text.lower() for keyword in psychology_keywords):
        # Psychology consultation
        thinking_msg = await update.message.reply_text("🤔 Анализирую вашу ситуацию...")
        
        prompt = get_psychology_consultation_prompt(text)
        response = await get_ai_response(prompt, max_tokens=500)
        
        await thinking_msg.delete()  # Удаляем сообщение "Анализирую..."
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        return WAITING_MESSAGE
    
    # Check message count for express analysis
    message_count = len(conversation_history[user.id])
    
    if message_count >= 10:
        # Trigger express analysis
        thinking_msg = await update.message.reply_text(
            "🎯 Отлично! У меня достаточно информации для экспресс-анализа. "
            "Провожу анализ вашей личности..."
        )
        
        conversation_text = " ".join(conversation_history[user.id])
        prompt = get_express_analysis_prompt(conversation_text, message_count)
        response = await get_ai_response(prompt, max_tokens=400)
        
        await thinking_msg.delete()  # Удаляем сообщение "Провожу анализ..."
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        
        # Offer full analysis
        await update.message.reply_text(
            "💎 **Хотите детальный анализ?**\n\n"
            "Полный психоанализ включает:\n"
            "• 7 профессиональных вопросов\n"
            "• Детальный профиль личности\n"
            "• HR-оценки и рекомендации\n"
            "• Образовательную траекторию\n\n"
            "Стоимость: 500₽\n"
            "Для заказа напишите: 'хочу полный анализ'"
        )
        
        # Save express analysis
        analysis_data = {
            'type': 'express',
            'conversation': conversation_text,
            'analysis': response,
            'message_count': message_count
        }
        save_analysis(user.id, user.first_name or f"User_{user.id}", 'express', analysis_data)
        
        return WAITING_MESSAGE
    
    # Continue conversation with smart questions
    if message_count in [3, 6, 8]:
        # Ask professional questions to guide conversation
        questions = [
            "Расскажите о ваших главных целях в жизни. Что для вас важно?",
            "Как вы обычно принимаете важные решения? Что влияет на ваш выбор?",
            "Опишите идеальную рабочую среду. Где вы чувствуете себя лучше всего?",
            "Что вас больше всего мотивирует? Откуда черпаете энергию?",
            "Какие ваши сильные стороны? В чем вы особенно хороши?"
        ]
        
        question = questions[min(message_count // 2, len(questions) - 1)]
        await update.message.reply_text(f"💭 {question}")
        return WAITING_MESSAGE
    
    # Smart AI response based on conversation
    thinking_msg = await update.message.reply_text("🤔 Думаю...")
    
    # Generate intelligent response
    conversation_text = " ".join(conversation_history[user.id][-5:])  # Last 5 messages
    prompt = f"""
Ты — профессиональный психолог-консультант с опытом HR. Твоя главная роль - ПСИХОЛОГИЧЕСКАЯ ПОДДЕРЖКА.

ДИАЛОГ:
{conversation_text}

ТВОИ РОЛИ (в порядке приоритета):
1. ПСИХОЛОГ - эмпатия, поддержка, понимание эмоций
2. ДРУГ - теплое общение, забота о человеке
3. КОНСУЛЬТАНТ - помощь с карьерой и развитием

ПРИНЦИПЫ:
- СНАЧАЛА прояви эмпатию и понимание
- НЕ навязывай карьерные темы, если человек не готов
- Поддерживай эмоционально
- Только потом мягко подводи к самоанализу

ФОРМАТ: Эмпатичный ответ (1-2 предложения) + мягкий вопрос.

СТИЛЬ: Теплый, понимающий, поддерживающий психолог.
"""
    
    response = await get_ai_response(prompt, max_tokens=200)
    await thinking_msg.delete()  # Удаляем сообщение "Думаю..."
    await update.message.reply_text(response)
    return WAITING_MESSAGE


async def handle_full_analysis_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    text = update.message.text.strip()
    
    if not text or len(text) < 20:
        await update.message.reply_text(
            "Пожалуйста, дайте развернутый ответ (минимум 20 символов). "
            "Это важно для качественного анализа."
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
        # All questions answered, conduct full analysis
        thinking_msg = await update.message.reply_text(
            "🎯 Отлично! Все ответы получены. "
            "Провожу детальный психоанализ... Это займет несколько минут."
        )
        
        prompt = get_full_analysis_prompt(answers)
        response = await get_ai_response(prompt, max_tokens=1500)
        
        await thinking_msg.delete()  # Удаляем сообщение "Провожу анализ..."
        
        # Split long response
        max_length = 4000
        if len(response) <= max_length:
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        else:
            parts = [response[i:i+max_length] for i in range(0, len(response), max_length)]
            for i, part in enumerate(parts):
                prefix = f"**Анализ (часть {i+1}):**\n\n" if i > 0 else ""
                await update.message.reply_text(prefix + part, parse_mode=ParseMode.MARKDOWN)
        
        # Save full analysis
        analysis_data = {
            'type': 'full',
            'answers': answers,
            'analysis': response
        }
        save_analysis(user.id, user.first_name or f"User_{user.id}", 'full', analysis_data, 'paid')
        
        await update.message.reply_text(
            "✅ **Анализ завершен!**\n\n"
            "Спасибо за доверие. Ваши данные сохранены анонимно.\n"
            "Для нового анализа используйте /start"
        )
        
        # Clear user data
        user_data.pop(user.id, None)
        return ConversationHandler.END

def main():
    # Initialize database
    init_database()
    
    # Create application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Conversation handler
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
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('clear', clear_memory))
    
    logger.info("HR-Психоаналитик запущен")
    application.run_polling()

if __name__ == "__main__":
    main()
