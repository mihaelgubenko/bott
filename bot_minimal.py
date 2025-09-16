import os
import re
import json
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)
import openai


# ENV
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HR_PASSWORD = os.getenv("HR_PASSWORD", "HR2024")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения")


# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


# Multilingual texts and questions
QUESTIONS = {
    'ru': [
        "Опишите себя в нескольких словах. Какие качества считаете главными в своём характере?",
        "Что вам даёт энергию в течение дня? Откуда черпаете силы и мотивацию?",
        "Что раздражает больше: хаос или рутина? Почему?",
        "Когда перед вами выбор — что делаете в первую очередь? Как принимаете решения?",
        "Вы чаще думаете о прошлом, настоящем или будущем? Пример, пожалуйста.",
        "Что предпочитаете: говорить или писать? Когда и почему?",
        "Как относитесь к контролю — любите управлять или предпочитаете свободу? Объясните.",
    ],
    'en': [
        "Describe yourself in a few words. What qualities do you consider most important in your character?",
        "What gives you energy during the day? Where do you draw strength and motivation from?",
        "What irritates you more: chaos or routine? Why?",
        "When faced with a choice, what do you do first? How do you make decisions?",
        "Do you think more about the past, present, or future? Please give an example.",
        "What do you prefer: speaking or writing? When and why?",
        "How do you feel about control - do you like to manage or prefer freedom? Explain.",
    ],
    'he': [
        "תאר את עצמך בכמה מילים. אילו תכונות אתה מחשיב הכי חשובות באופי שלך?",
        "מה נותן לך אנרגיה במהלך היום? מאיפה אתה שואב כוח ומוטיבציה?",
        "מה מעצבן אותך יותר: כאוס או שגרה? למה?",
        "כשאתה עומד בפני בחירה - מה אתה עושה קודם? איך אתה מקבל החלטות?",
        "אתה חושב יותר על העבר, ההווה או העתיד? בבקשה תן דוגמה.",
        "מה אתה מעדיף: לדבר או לכתוב? מתי ולמה?",
        "איך אתה מתייחס לשליטה - אתה אוהב לנהל או מעדיף חופש? הסבר.",
    ]
}

QUESTIONS_RU = QUESTIONS['ru']  # Backward compatibility

# Language detection
def detect_language(text: str) -> str:
    """Определяет язык текста по символам"""
    if not text or text.strip() in ['/start', '/help', '/cancel']:
        return 'ru'
    
    text = text.strip()
    
    # Проверяем наличие ивритских символов
    if any('\u0590' <= char <= '\u05FF' for char in text):
        return 'he'
    
    # Проверяем наличие кириллицы
    if any('\u0400' <= char <= '\u04FF' for char in text):
        return 'ru'
    
    # Проверяем английские слова
    english_words = ['hello', 'hi', 'start', 'help', 'test', 'analysis', 'career', 'psychology']
    if any(word in text.lower() for word in english_words):
        return 'en'
    
    # По умолчанию русский для коротких сообщений
    return 'ru'

# Multilingual texts
TEXTS = {
    'ru': {
        'help': (
            "🤖 Возможности:\n"
            "• Экспресс-анализ сообщений\n"
            "• Полный опрос из 7 вопросов (Фрейд, Юнг, MBTI, Big Five, HR)\n"
            "• HR-оценки и рекомендации по найму\n"
            "• Сохранение результатов в базе данных\n\n"
            "Как пользоваться:\n"
            "1) Выберите формат — экспресс или полный опрос.\n"
            "2) Отвечайте развёрнуто — так анализ точнее.\n"
            "3) Можно просто общаться — бот задаёт умные вопросы.\n"
            "4) После 3 сообщений — принудительный выбор анализа.\n\n"
            "HR-команды (только для администраторов):\n"
            "• /hr_panel HR2024 — просмотр всех кандидатов\n"
            "• /hr_compare HR2024 — сравнение кандидатов\n\n"
            "Важно: это не медицинская помощь. Ответы — краткие и поддерживающие."
        ),
        'greet': (
            "🎯 Карьерный психоаналитик\n\n"
            "Определю ваш психотип и подходящие роли. Выберите формат:\n"
        ),
        'buttons': {
            'express': '⚡ Экспресс-анализ',
            'full_test': '📋 Полный тест',
            'help': '📘 Справка',
            'back': '⬅️ Назад',
            'continue': '💬 Еще поговорить'
        }
    },
    'en': {
        'help': (
            "🤖 Features:\n"
            "• Express message analysis\n"
            "• Full 7-question survey (Freud, Jung, MBTI, Big Five, HR)\n"
            "• HR scores and hiring recommendations\n"
            "• Results saved to database\n\n"
            "How to use:\n"
            "1) Choose format — express or full survey.\n"
            "2) Answer in detail — more accurate analysis.\n"
            "3) Just chat — bot asks smart questions.\n"
            "4) After 3 messages — forced analysis choice.\n\n"
            "HR commands (admin only):\n"
            "• /hr_panel HR2024 — view all candidates\n"
            "• /hr_compare HR2024 — compare candidates\n\n"
            "Important: This is not medical advice. Responses are brief and supportive."
        ),
        'greet': (
            "🎯 Career Psychoanalyst\n\n"
            "I'll determine your psychotype and suitable roles. Choose format:\n"
        ),
        'buttons': {
            'express': '⚡ Express Analysis',
            'full_test': '📋 Full Test',
            'help': '📘 Help',
            'back': '⬅️ Back',
            'continue': '💬 Keep Chatting'
        }
    },
    'he': {
        'help': (
            "🤖 יכולות:\n"
            "• ניתוח מהיר של הודעות\n"
            "• סקר מלא של 7 שאלות (פרויד, יונג, MBTI, Big Five, HR)\n"
            "• ציוני HR והמלצות לגיוס\n"
            "• שמירת תוצאות במסד נתונים\n\n"
            "איך להשתמש:\n"
            "1) בחר פורמט — מהיר או סקר מלא.\n"
            "2) ענה בפירוט — ניתוח מדויק יותר.\n"
            "3) פשוט תשוחח — הבוט שואל שאלות חכמות.\n"
            "4) אחרי 3 הודעות — בחירה כפויה של ניתוח.\n\n"
            "פקודות HR (למנהלים בלבד):\n"
            "• /hr_panel HR2024 — צפייה בכל המועמדים\n"
            "• /hr_compare HR2024 — השוואת מועמדים\n\n"
            "חשוב: זה לא ייעוץ רפואי. תגובות קצרות ותומכות."
        ),
        'greet': (
            "🎯 פסיכואנליטיקאי קריירה\n\n"
            "אקבע את הפסיכוטיפ שלך ותפקידים מתאימים. בחר פורמט:\n"
        ),
        'buttons': {
            'express': '⚡ ניתוח מהיר',
            'full_test': '📋 מבחן מלא',
            'help': '📘 עזרה',
            'back': '⬅️ חזור',
            'continue': '💬 להמשיך לשוחח'
        }
    }
}

HELP_TEXT_RU = TEXTS['ru']['help']  # Backward compatibility
GREET_RU = TEXTS['ru']['greet']  # Backward compatibility


# States for ConversationHandler
(Q1, Q2, Q3, Q4, Q5, Q6, Q7) = range(7)


# In-memory storage
user_answers = {}
conversation_history = {}

# Database functions
def init_database():
    conn = sqlite3.connect('candidates.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            language TEXT DEFAULT 'ru',
            analysis_data TEXT,
            hr_scores TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_candidate(telegram_id: int, name: str, language: str, analysis_data: dict, hr_scores: dict):
    conn = sqlite3.connect('candidates.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO candidates 
        (telegram_id, name, language, analysis_data, hr_scores, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, name, language, json.dumps(analysis_data), json.dumps(hr_scores), datetime.now()))
    conn.commit()
    conn.close()

def get_all_candidates():
    conn = sqlite3.connect('candidates.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    candidates = cursor.fetchall()
    conn.close()
    return candidates

def calculate_hr_scores(analysis_text: str) -> dict:
    """Извлекает HR-оценки из анализа текста"""
    scores = {
        'leadership': 5, 'teamwork': 5, 'stress_resistance': 5, 'motivation': 5,
        'communication': 5, 'adaptability': 5, 'reliability': 5, 'creativity': 5,
        'analytical_thinking': 5, 'emotional_intelligence': 5
    }
    
    # Простая логика на основе ключевых слов
    text_lower = analysis_text.lower()
    
    # Лидерство
    if any(word in text_lower for word in ['лидер', 'руковод', 'управл', 'ведущ']):
        scores['leadership'] = 8
    elif any(word in text_lower for word in ['последователь', 'подчинен', 'исполнитель']):
        scores['leadership'] = 3
    
    # Командная работа
    if any(word in text_lower for word in ['команд', 'коллектив', 'сотруднич', 'взаимодейств']):
        scores['teamwork'] = 8
    elif any(word in text_lower for word in ['одиночк', 'индивидуал', 'самостоятельн']):
        scores['teamwork'] = 3
    
    # Стрессоустойчивость
    if any(word in text_lower for word in ['стресс', 'давлен', 'нагрузк', 'спокойн', 'устойчив']):
        scores['stress_resistance'] = 8
    elif any(word in text_lower for word in ['тревожн', 'волнен', 'нервн', 'переживан']):
        scores['stress_resistance'] = 3
    
    return scores


def get_navigation_keyboard(current_index: int, language: str = 'ru') -> InlineKeyboardMarkup | None:
    if current_index > 0:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(TEXTS[language]['buttons']['back'], callback_data=f"back_{current_index-1}")]]
        )
    return None


def get_start_keyboard(language: str = 'ru') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(TEXTS[language]['buttons']['express'], callback_data='express_analysis')],
            [InlineKeyboardButton(TEXTS[language]['buttons']['full_test'], callback_data='full_test')],
            [InlineKeyboardButton(TEXTS[language]['buttons']['help'], callback_data='help_show')],
        ]
    )


def is_valid_answer(text: str, min_words: int = 3) -> tuple[bool, str]:
    if not text or not text.strip():
        return False, "empty"
    words = text.strip().split()
    if len(words) < min_words:
        return False, "too_short"
    if len(text.strip()) < 10:
        return False, "too_short_chars"
    meaningless_patterns = [r'^\d+$', r'^[.,!?;:\s]*$', r'^(.)\1{10,}', r'asdf|qwerty|123|тест|test']
    tl = text.lower()
    for p in meaningless_patterns:
        if re.search(p, tl):
            return False, "meaningless"
    return True, "valid"


def analyze_speech_style(text: str) -> str:
    words = text.split()
    sentences = [s for s in re.split(r'[.!?]', text) if s.strip()]
    emotional_markers = len(re.findall(r'[!?]{1,3}', text))
    pronouns = len(re.findall(r'\b(я|мне|мой|моя|мои|меня|мной)\b', text.lower()))
    complexity = 'высокая' if len(words) > 200 else 'средняя' if len(words) > 100 else 'низкая'
    return (
        f"📊 Анализ речи:\n"
        f"• Объём текста: {len(words)} слов\n"
        f"• Сложность речи: {complexity}\n"
        f"• Эмоциональность: {'высокая' if emotional_markers > 5 else 'умеренная'}\n"
        f"• Самофокусированность: {'высокая' if pronouns > 10 else 'умеренная'}"
    )


async def think_and_respond(message_text: str) -> str:
    prompt = (
        f"Ты психоаналитик и HR-консультант. Пользователь написал: \"{message_text}\"\n\n"
        "ПРАВИЛА:\n"
        "1) Сначала ответь на прямой вопрос (если есть)\n"
        "2) Затем короткий анализ (1–2 предложения)\n"
        "3) Задай ОДИН уточняющий вопрос\n"
        "4) Всего до 3 предложений, мягкий тон"
    )
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
            timeout=30,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка think_and_respond: {e}")
        return "Понимаю. Могу провести психологический анализ. Нажмите /start и выберите формат."


async def process_express_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msgs = conversation_history.get(user.id, [])
    if not msgs:
        await update.message.reply_text(
            "⚡ Экспресс-анализ: расскажите, что вас вдохновляет, какие задачи радуют и о каких целях мечтаете.")
        return
    dialog_text = " \n".join(msgs)
    speech = analyze_speech_style(" ".join(msgs))
    prompt = f"""
Ты комбинированный эксперт: психоаналитик (Фрейд, Юнг) + HR-специалист + MBTI + Big Five.

ДИАЛОГ ПОЛЬЗОВАТЕЛЯ:
{dialog_text}

ЦЕЛИ:
1) Психоанализ: психотип, архетип, защитные механизмы
2) HR-оценка: потенциал, роли, рекомендации для найма

УЧТИ ЛИНГВИСТИЧЕСКИЙ АНАЛИЗ:
{speech}

ФОРМАТ ОТВЕТА:
🎯 ЭКСПРЕСС-ПРОФИЛЬ
🧠 Психотип: [MBTI] — [архетип]
📊 Big Five: O[X] C[X] E[X] A[X] N[X]
💼 HR-оценки: Лидерство [X/10], Команда [X/10], Стресс [X/10]
🎯 Профессии: [3 конкретные с кратким обоснованием]
✅ Рекомендация: [РЕКОМЕНДОВАН/УСЛОВНО/НЕ РЕКОМЕНДОВАН] + причина
Кратко и по делу.
"""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7,
            timeout=60,
        )
        analysis_text = resp.choices[0].message.content.strip()
        await update.message.reply_text(analysis_text, parse_mode=ParseMode.MARKDOWN)
        
        # Сохраняем в БД
        user = update.effective_user
        language = context.user_data.get('language', 'ru')
        hr_scores = calculate_hr_scores(analysis_text)
        analysis_data = {
            'type': 'express',
            'text': analysis_text,
            'conversation': dialog_text
        }
        save_candidate(
            telegram_id=user.id,
            name=user.first_name or f"User_{user.id}",
            language=language,
            analysis_data=analysis_data,
            hr_scores=hr_scores
        )
        
    except Exception as e:
        logger.error(f"Ошибка экспресс-анализа: {e}")
        await update.message.reply_text("❌ Ошибка экспресс-анализа. Попробуйте полный опрос.")


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, language: str = 'ru') -> None:
    text = TEXTS[language]['greet']
    
    if update.message:
        await update.message.reply_text(text, reply_markup=get_start_keyboard(language), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=get_start_keyboard(language), parse_mode=ParseMode.MARKDOWN)


# COMMANDS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_answers.pop(user.id, None)
    conversation_history.pop(user.id, None)
    
    # Для команды /start всегда используем русский по умолчанию
    # Язык определится при первом текстовом сообщении
    language = 'ru'
    context.user_data['language'] = language
    
    await show_main_menu(update, context, language)
    return Q1


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text if update.message else ""
    language = detect_language(text)
    await update.message.reply_text(TEXTS[language]['help'])

async def hr_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """HR-панель для просмотра кандидатов"""
    user = update.effective_user
    if str(user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Доступ запрещён. Эта функция только для HR-специалистов.")
        return
    
    password = context.args[0] if context.args else ""
    if password != HR_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль. Используйте: /hr_panel HR2024")
        return
    
    candidates = get_all_candidates()
    if not candidates:
        await update.message.reply_text("📊 HR-панель\n\nКандидатов пока нет.")
        return
    
    text = "📊 **HR-панель** - Все кандидаты:\n\n"
    for i, candidate in enumerate(candidates[:10], 1):  # Показываем последних 10
        name = candidate[2] or f"Пользователь {candidate[1]}"
        created = candidate[6].split()[0] if candidate[6] else "Неизвестно"
        text += f"{i}. **{name}**\n"
        text += f"   ID: {candidate[1]}\n"
        text += f"   Дата: {created}\n"
        text += f"   Язык: {candidate[3]}\n\n"
    
    if len(candidates) > 10:
        text += f"... и ещё {len(candidates) - 10} кандидатов"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def hr_compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сравнение кандидатов"""
    user = update.effective_user
    if str(user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Доступ запрещён. Эта функция только для HR-специалистов.")
        return
    
    password = context.args[0] if context.args else ""
    if password != HR_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль. Используйте: /hr_compare HR2024")
        return
    
    candidates = get_all_candidates()
    if len(candidates) < 2:
        await update.message.reply_text("📊 Для сравнения нужно минимум 2 кандидата.")
        return
    
    text = "📊 **Сравнение кандидатов**\n\n"
    for i, candidate in enumerate(candidates[:5], 1):  # Сравниваем последних 5
        name = candidate[2] or f"Пользователь {candidate[1]}"
        hr_scores = json.loads(candidate[5]) if candidate[5] else {}
        
        text += f"**{i}. {name}**\n"
        text += f"Лидерство: {hr_scores.get('leadership', 5)}/10\n"
        text += f"Команда: {hr_scores.get('teamwork', 5)}/10\n"
        text += f"Стресс: {hr_scores.get('stress_resistance', 5)}/10\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Состояние сброшено. Для нового анализа используйте /start")
    user = update.effective_user
    user_answers.pop(user.id, None)
    conversation_history.pop(user.id, None)
    return ConversationHandler.END


# CALLBACKS
async def help_show_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(HELP_TEXT_RU)


async def continue_chat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("💬 Продолжаем диалог. Поделитесь мыслями — задам профессиональные вопросы.")


async def full_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    
    language = context.user_data.get('language', 'ru')
    questions = QUESTIONS[language]
    
    await q.edit_message_text(
        f"📋 Начинаем опрос (1/7)\n\n{questions[0]}",
        reply_markup=get_navigation_keyboard(0, language),
    )
    context.user_data['state'] = 0
    return Q1


async def express_analysis_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🔄 Собираю ваши последние сообщения для экспресс-анализа...")
    # Следующее сообщение пользователя запустит анализ
    context.user_data['waiting_express'] = True
    return Q1


async def handle_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    idx = int(q.data.split('_')[1])
    context.user_data['state'] = idx
    await q.edit_message_text(
        f"⬅️ Вернулись к вопросу {idx+1}/7. Дайте новый ответ:\n\n{QUESTIONS_RU[idx]}",
        reply_markup=get_navigation_keyboard(idx),
    )
    return idx


# SURVEY FLOW
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    text = (update.message.text or "").strip()

    # Определяем язык
    language = detect_language(text)
    context.user_data['language'] = language

    # Accumulate chat history for express mode
    history = conversation_history.setdefault(user.id, [])
    history.append(text)
    if len(history) > 10:
        conversation_history[user.id] = history[-10:]

    # If waiting for express data
    if context.user_data.get('waiting_express'):
        context.user_data['waiting_express'] = False
        await update.message.reply_text("🔄 Анализирую ваши сообщения...")
        await process_express_analysis(update, context)
        return ConversationHandler.END

    # If survey not started yet, start smart chat response
    if 'state' not in context.user_data:
        # Smart short reply with suggestions and buttons at milestones
        thinking_msg = await update.message.reply_text("🤔 Думаю...")
        smart = await think_and_respond(text)
        await thinking_msg.delete()

        msg_count = len(history)
        if msg_count >= 3:  # Принудительный выбор после 3 сообщений
            keyboard = [
                [InlineKeyboardButton(TEXTS[language]['buttons']['express'], callback_data='express_analysis')],
                [InlineKeyboardButton(TEXTS[language]['buttons']['full_test'], callback_data='full_test')],
            ]
            if msg_count < 5:
                keyboard.append([InlineKeyboardButton(TEXTS[language]['buttons']['continue'], callback_data='continue_chat')])
            
            await update.message.reply_text(
                f"{smart}\n\n🎯 **Время для анализа!** Выберите формат:", 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode=ParseMode.MARKDOWN
            )
        elif msg_count >= 6:  # Автоматический экспресс после 6 сообщений
            await update.message.reply_text("🎯 **Автоматический анализ** - достаточно данных. Запускаю экспресс-анализ...")
            await process_express_analysis(update, context)
        else:
            await update.message.reply_text(smart)
        return ConversationHandler.END

    # Survey in progress
    state = context.user_data.get('state', 0)
    is_valid, err = is_valid_answer(text)
    if not is_valid:
        errors = {
            'too_short': "❌ Дайте более развёрнутый ответ (минимум 3 слова).",
            'too_short_chars': "❌ Ответ слишком короткий. Напишите минимум 10 символов.",
            'meaningless': "❌ Пожалуйста, дайте осмысленный ответ.",
            'empty': "❌ Вы не написали ответ. Пожалуйста, ответьте на вопрос.",
        }
        await update.message.reply_text(
            errors.get(err, errors['too_short']), reply_markup=get_navigation_keyboard(state, language)
        )
        return state

    answers = user_answers.setdefault(user.id, [None] * 7)
    answers[state] = text

    if state < 6:
        next_state = state + 1
        context.user_data['state'] = next_state
        questions = QUESTIONS[language]
        await update.message.reply_text(
            f"{next_state+1}/7. {questions[next_state]}",
            reply_markup=get_navigation_keyboard(next_state, language),
        )
        return next_state
    else:
        await update.message.reply_text("🔄 Анализирую ваши ответы... Это займёт несколько секунд.")
        await process_full_analysis(update, context)
        return ConversationHandler.END


async def process_full_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    answers = user_answers.get(user.id, [])
    if len(answers) != 7 or any(a is None for a in answers):
        await update.message.reply_text("❌ Не все ответы получены. Начните заново с /start")
        return
    
    language = context.user_data.get('language', 'ru')
    questions = QUESTIONS[language]
    answers_block = "\n".join(
        f"{i+1}) {q}\nОтвет: {a}\n" for i, (q, a) in enumerate(zip(questions, answers))
    )
    speech = analyze_speech_style(" ".join(answers))
    prompt = f"""
Ты — ведущий психолог-профайлер, специалист в психоанализе (Фрейд, Юнг), MBTI, Big Five и HR.

Проведи глубокий анализ и дай практичные рекомендации.

ОБЯЗАТЕЛЬНЫЙ ФОРМАТ:
---
🧠 ПСИХОАНАЛИТИЧЕСКИЙ ПРОФИЛЬ:
Структура личности: [Ид/Эго/Суперэго + обоснование]
Защитные механизмы: [2–3 механизма с примерами]
Бессознательные конфликты: [кратко]

🎭 АРХЕТИП И ТИПОЛОГИЯ:
Архетип по Юнгу: [описание]
MBTI: [код + объяснение]
Темперамент: [тип + обоснование]

📊 BIG FIVE (OCEAN):
Открытость: [1–10]\nДобросовестность: [1–10]\nЭкстраверсия: [1–10]\nДоброжелательность: [1–10]\nНейротизм: [1–10]

🗣️ ЛИНГВИСТИКА:
{speech}

💼 HR-РЕКОМЕНДАЦИИ:
Подходящие сферы: [кратко]\nКонкретные профессии: [3–5 с обоснованием]\nНавыки/обучение: [направления]\nСтратегия роста: [шаги]

🔮 ПРОГНОЗ ПОВЕДЕНИЯ:
В стрессе / В команде / В отношениях: [кратко]
---

ОТВЕТЫ ПОЛЬЗОВАТЕЛЯ:
{answers_block}
"""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.7,
            timeout=120,
        )
        analysis = resp.choices[0].message.content.strip()
        # Split long message safely
        max_len = 3800
        if len(analysis) <= max_len:
            await update.message.reply_text(analysis, parse_mode=ParseMode.MARKDOWN)
        else:
            start = 0
            part = 1
            while start < len(analysis):
                chunk = analysis[start:start + max_len]
                prefix = "" if part == 1 else f"\n\n📋 Продолжение ({part}):\n\n"
                await update.message.reply_text(prefix + chunk, parse_mode=ParseMode.MARKDOWN)
                start += max_len
                part += 1
        await update.message.reply_text("✅ Анализ завершён. Для нового анализа используйте /start")
        
        # Сохраняем в БД
        hr_scores = calculate_hr_scores(analysis)
        analysis_data = {
            'type': 'full',
            'text': analysis,
            'answers': answers
        }
        save_candidate(
            telegram_id=user.id,
            name=user.first_name or f"User_{user.id}",
            language=language,
            analysis_data=analysis_data,
            hr_scores=hr_scores
        )
        
    except Exception as e:
        logger.error(f"Ошибка полного анализа: {e}")
        await update.message.reply_text("❌ Ошибка анализа. Попробуйте позже.")
    finally:
        user_answers.pop(user.id, None)


# GENERAL CHAT HANDLER
async def handle_general_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Опишите, пожалуйста, вашу ситуацию или вопрос.")
        return ConversationHandler.END

    # Определяем язык
    language = detect_language(text)
    context.user_data['language'] = language

    history = conversation_history.setdefault(user.id, [])
    history.append(text)
    if len(history) > 10:
        conversation_history[user.id] = history[-10:]

    thinking_msg = await update.message.reply_text("🤔 Думаю...")
    smart = await think_and_respond(text)
    await thinking_msg.delete()

    msg_count = len(history)
    if msg_count in (3, 5):
        keyboard = [
            [InlineKeyboardButton(TEXTS[language]['buttons']['express'], callback_data='express_analysis')],
            [InlineKeyboardButton(TEXTS[language]['buttons']['full_test'], callback_data='full_test')],
            [InlineKeyboardButton(TEXTS[language]['buttons']['continue'], callback_data='continue_chat')],
        ]
        await update.message.reply_text(
            f"{smart}\n\nВыберите действие:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )
    elif msg_count >= 6:
        await update.message.reply_text("🎯 Достаточно данных. Запускаю экспресс-анализ...")
        await process_express_analysis(update, context)
    else:
        await update.message.reply_text(smart)

    return ConversationHandler.END


def main() -> None:
    # Инициализация БД
    init_database()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands (кроме start - он в ConversationHandler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("hr_panel", hr_panel_command))
    application.add_handler(CommandHandler("hr_compare", hr_compare_command))

    # Conversation handler for survey and callbacks
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Q1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$"),
                CallbackQueryHandler(full_test_callback, pattern='full_test'),
                CallbackQueryHandler(express_analysis_callback, pattern='express_analysis'),
                CallbackQueryHandler(continue_chat_callback, pattern='continue_chat'),
                CallbackQueryHandler(help_show_callback, pattern='help_show'),
            ],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            Q6: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            Q7: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    application.add_handler(conv)

    # Out of conversation generic messages (только если не в ConversationHandler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message))

    logger.info("Бот запущен (расширенный RU)")
    application.run_polling(allowed_updates=['message', 'callback_query'])


if __name__ == "__main__":
    main()
