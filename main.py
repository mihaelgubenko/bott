import logging
import os
import re
from dotenv import load_dotenv
from telegram import Update, ForceReply, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)
import openai
from telegram.constants import ParseMode

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# Проверка наличия всех необходимых переменных окружения
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в .env файле!")
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID не найден в .env файле!")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    raise ValueError("ADMIN_CHAT_ID должен быть числом!")

# Вопросы опроса на разных языках
QUESTIONS = {
    'ru': [
        "Опиши себя в нескольких словах. Какие качества считаешь главными в своём характере?",
        "Что тебе даёт энергию в течение дня? Откуда черпаешь силы и мотивацию?",
        "Что тебя больше раздражает: хаос или рутина? Почему именно это?",
        "Когда перед тобой выбор, что ты делаешь в первую очередь? Как принимаешь решения?",
        "Ты чаще думаешь о прошлом, настоящем или будущем? Приведи пример.",
        "Что ты предпочитаешь: говорить или писать? В каких ситуациях и почему?",
        "Как ты относишься к контролю — любишь управлять или предпочитаешь свободу? Объясни свою позицию."
    ],
    'he': [
        "תאר את עצמך במספר מילים. אילו תכונות אתה רואה כעיקריות באופי שלך?",
        "מה נותן לך אנרגיה במהלך היום? מאיפה אתה שואב כוח ומוטיבציה?",
        "מה מרגיז אותך יותר: כאוס או שגרה? למה דווקא זה?",
        "כשעומד לפניך בחירה, מה אתה עושה קודם כל? איך אתה מקבל החלטות?",
        "אתה חושב יותר על העבר, ההווה או העתיד? תן דוגמה.",
        "מה אתה מעדיף: לדבר או לכתוב? באילו מצבים ולמה?",
        "איך אתה מתייחס לשליטה - אתה אוהב לנהל או מעדיף חופש? הסבר את העמדה שלך."
    ],
    'en': [
        "Describe yourself in a few words. What qualities do you consider main in your character?",
        "What gives you energy during the day? Where do you draw strength and motivation from?",
        "What annoys you more: chaos or routine? Why exactly this?",
        "When faced with a choice, what do you do first? How do you make decisions?",
        "Do you think more about the past, present, or future? Give an example.",
        "What do you prefer: speaking or writing? In what situations and why?",
        "How do you feel about control - do you like to manage or prefer freedom? Explain your position."
    ]
}

GREETINGS = {
    'ru': """🔬 **Добро пожаловать в профессиональный психологический анализ!**

Это конфиденциальный опрос для глубокого анализа личности. Ваши ответы анонимны и будут удалены после анализа.

📋 Используйте /help для справки о возможностях бота.""",
    'he': """🔬 **ברוכים הבאים לניתוח פסיכולוגי מקצועי!**

זהו סקר סודי לניתוח עמוק של האישיות. התשובות שלכם אנונימיות וימחקו לאחר הניתוח.

📋 השתמשו ב-/help למידע על יכולות הבוט.""",
    'en': """🔬 **Welcome to professional psychological analysis!**

This is a confidential survey for deep personality analysis. Your answers are anonymous and will be deleted after analysis.

📋 Use /help for bot capabilities info."""
}

HELP_TEXT = {
    'ru': """🤖 **Возможности психоаналитического бота:**

🔍 **Что я умею:**
• Глубокий психологический анализ личности
• Профайлинг по методикам Фрейда, Юнга, Майерс-Бриггс
• Анализ стиля речи и языковых паттернов
• Определение темперамента и архетипа личности
• Выявление защитных механизмов психики
• Рекомендации по личностному развитию

📋 **Как это работает:**
1. Отвечайте на 7 вопросов максимально подробно
2. Пишите развёрнуто — чем больше текста, тем точнее анализ
3. Будьте честными — анализ анонимен и конфиденциален
4. После анализа все ваши данные автоматически удаляются

🔒 **Конфиденциальность:**
• Ваши ответы не сохраняются в базе данных
• После анализа все данные стираются из памяти
• Анализ проводится с помощью ИИ без участия людей

⬅️ **Навигация:**
• Используйте кнопку "Назад" для исправления предыдущего ответа
• Команда /cancel для отмены опроса
• Команда /start для нового анализа

🌐 **Языки:** Русский, Иврит, English (автоопределение)

Для начала анализа напишите /start""",
    
    'he': """🤖 **יכולות הבוט הפסיכואנליטי:**

🔍 **מה אני יודע לעשות:**
• ניתוח פסיכולוגי עמוק של האישיות
• פרופיילינג לפי שיטות פרויד, יונג, מאיירס-בריגס
• ניתוח סגנון דיבור ודפוסים לשוניים
• קביעת טמפרמנט וארכיטיפ אישיות
• זיהוי מנגנוני הגנה נפשיים
• המלצות לפיתוח אישי

📋 **איך זה עובד:**
1. ענו על 7 שאלות בפירוט מירבי
2. כתבו בהרחבה - ככל שיש יותר טקסט, הניתוח מדויק יותר
3. היו כנים - הניתוח אנונימי וסודי
4. לאחר הניתוח כל הנתונים שלכם נמחקים אוטומטית

🔒 **סודיות:**
• התשובות שלכם לא נשמרות בבסיס נתונים
• לאחר הניתוח כל הנתונים נמחקים מהזיכרון
• הניתוח מתבצע באמצעות בינה מלאכותית ללא השתתפות אנשים

⬅️ **ניווט:**
• השתמשו בכפתור "אחורה" לתיקון התשובה הקודמת
• פקודה /cancel לביטול הסקר
• פקודה /start לניתוח חדש

🌐 **שפות:** רוסית, עברית, English (זיהוי אוטומטי)

להתחלת ניתוח כתבו /start""",
    
    'en': """🤖 **Psychoanalytic Bot Capabilities:**

🔍 **What I can do:**
• Deep psychological personality analysis
• Profiling using Freud, Jung, Myers-Briggs methods
• Speech style and linguistic pattern analysis
• Temperament and personality archetype determination
• Identification of psychological defense mechanisms
• Personal development recommendations

📋 **How it works:**
1. Answer 7 questions in maximum detail
2. Write extensively - the more text, the more accurate the analysis
3. Be honest - analysis is anonymous and confidential
4. After analysis, all your data is automatically deleted

🔒 **Confidentiality:**
• Your answers are not stored in database
• After analysis, all data is erased from memory
• Analysis is performed by AI without human involvement

⬅️ **Navigation:**
• Use "Back" button to correct previous answer
• Command /cancel to cancel survey
• Command /start for new analysis

🌐 **Languages:** Русский, עברית, English (auto-detection)

To start analysis, type /start"""
}

# Состояния для ConversationHandler
(Q1, Q2, Q3, Q4, Q5, Q6, Q7) = range(7)

# Временное хранилище ответов
user_data = {}

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def detect_language(text):
    """Определение языка по тексту"""
    # Считаем количество символов каждого языка
    russian_chars = len(re.findall(r'[а-яё]', text.lower()))
    hebrew_chars = len(re.findall(r'[א-ת]', text))
    english_chars = len(re.findall(r'[a-z]', text.lower()))
    
    total_letters = russian_chars + hebrew_chars + english_chars
    
    # Если слишком мало букв, возвращаем русский по умолчанию
    if total_letters < 5:
        return 'ru'
    
    # Определяем язык по преобладающим символам
    if russian_chars > max(hebrew_chars, english_chars):
        return 'ru'
    elif hebrew_chars > max(russian_chars, english_chars):
        return 'he'
    elif english_chars > max(russian_chars, hebrew_chars):
        return 'en'
    else:
        return 'ru'  # По умолчанию русский

def is_valid_answer(text, min_words=3):
    """Проверка валидности ответа"""
    if not text or text.strip() == "":
        return False, "empty"
    
    words = text.strip().split()
    if len(words) < min_words:
        return False, "too_short"
    
    # Проверка на бессмысленные ответы
    meaningless_patterns = [
        r'^\d+$',       # только цифры
        r'^[.,!?;:\s]*$',  # только знаки препинания
        r'^(.)\1{10,}',    # повторяющиеся символы
        r'asdf|qwerty|123|test|тест|проверка|xnj',  # стандартные тестовые строки
    ]
    
    text_lower = text.lower()
    for pattern in meaningless_patterns:
        if re.search(pattern, text_lower):
            return False, "meaningless"
    
    # Проверка на слишком короткие ответы (менее 10 символов)
    if len(text.strip()) < 10:
        return False, "too_short_chars"
    
    return True, "valid"

def get_navigation_keyboard(current_question, user_lang):
    """Создание клавиатуры с навигацией"""
    keyboard = []
    
    if current_question > 0:
        back_text = {
            'ru': '⬅️ Назад',
            'he': '⬅️ אחורה', 
            'en': '⬅️ Back'
        }
        keyboard.append([InlineKeyboardButton(back_text[user_lang], callback_data=f"back_{current_question-1}")])
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None

async def think_and_respond(user_message, user_lang='ru'):
    """Функция для 'размышления' бота через GPT"""
    thinking_prompts = {
        'ru': f"""Ты психологический бот-консультант. Пользователь написал: "{user_message}"

Проанализируй его сообщение и дай умный, эмпатичный ответ как профессиональный психолог:
- Если это вопрос о возможностях - объясни что ты умеешь
- Если это просто приветствие - поприветствуй дружелюбно
- Если это личный вопрос - дай краткий психологический совет
- Если просят помощь - предложи начать анализ
- Всегда отвечай на русском языке
- Будь теплым, профессиональным и полезным
- Ответ должен быть 1-3 предложения

Ответь ТОЛЬКО текстом ответа, без дополнительных комментариев.""",
        
        'he': f"""אתה בוט פסיכולוגי-יועץ. המשתמש כתב: "{user_message}"

נתח את ההודעה שלו ותן תשובה חכמה ואמפטית כפסיכולוג מקצועי:
- אם זה שאלה על יכולות - הסבר מה אתה יודע לעשות
- אם זה רק ברכה - בירך בידידותיות
- אם זה שאלה אישית - תן עצה פסיכולוגית קצרה
- אם מבקשים עזרה - הצע להתחיל בניתוח
- תמיד תשב בעברית
- היה חם, מקצועי ומועיל
- התשובה צריכה להיות 1-3 משפטים

תשב רק בטקסט התשובה, בלי הערות נוספות.""",
        
        'en': f"""You are a psychological counselor bot. The user wrote: "{user_message}"

Analyze their message and give a smart, empathetic response as a professional psychologist:
- If it's a question about capabilities - explain what you can do
- If it's just a greeting - greet friendly
- If it's a personal question - give brief psychological advice
- If asking for help - suggest starting analysis
- Always respond in English
- Be warm, professional and helpful
- Response should be 1-3 sentences

Respond ONLY with the answer text, no additional comments."""
    }
    
    # Защита от неизвестных языков
    if user_lang not in thinking_prompts:
        user_lang = 'ru'
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": thinking_prompts[user_lang]}],
            max_tokens=200,
            temperature=0.7,
            timeout=30
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка в think_and_respond: {e}")
        fallback_responses = {
            'ru': "Понимаю! Я здесь, чтобы помочь с психологическим анализом. Напишите /start для начала профессионального анализа личности.",
            'he': "מבין! אני כאן כדי לעזור בניתוח פסיכולוגי. כתבו /start להתחלת ניתוח מקצועי של האישיות.",
            'en': "I understand! I'm here to help with psychological analysis. Type /start to begin professional personality analysis."
        }
        return fallback_responses.get(user_lang, fallback_responses['ru'])

async def handle_general_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений вне опроса"""
    user_message = update.message.text
    user_lang = context.user_data.get('language', detect_language(user_message))
    
    # Сохраняем определенный язык
    context.user_data['language'] = user_lang
    
    # Показываем "думает..."
    thinking_messages = {
        'ru': "🤔 Думаю...",
        'he': "🤔 חושב...",
        'en': "🤔 Thinking..."
    }
    
    # Защита от неизвестных языков
    if user_lang not in thinking_messages:
        user_lang = 'ru'
    
    thinking_msg = await update.message.reply_text(thinking_messages[user_lang])
    
    # Получаем умный ответ
    smart_response = await think_and_respond(user_message, user_lang)
    
    # Удаляем "думает" и отправляем ответ
    await thinking_msg.delete()
    await update.message.reply_text(smart_response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    # Определяем язык по команде или предыдущим сообщениям
    user_lang = context.user_data.get('language', 'ru')
    await update.message.reply_text(HELP_TEXT[user_lang], parse_mode=ParseMode.MARKDOWN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    
    # Очищаем предыдущие данные если есть
    user_data.pop(user.id, None)
    context.user_data.clear()
    
    # Устанавливаем русский по умолчанию
    user_lang = 'ru'
    context.user_data['language'] = user_lang
    context.user_data['state'] = 0
    context.user_data['language_detected'] = False
    context.user_data['survey_started'] = False
    
    # Инициализируем данные пользователя
    user_data[user.id] = {'answers': [None] * 7, 'language': user_lang}
    
    # Отправляем только приветствие с кнопкой для начала
    start_button_text = {
        'ru': '🚀 Начать анализ',
        'he': '🚀 התחל ניתוח',
        'en': '🚀 Start Analysis'
    }
    
    # Защита от неизвестных языков
    if user_lang not in start_button_text:
        user_lang = 'ru'
    
    keyboard = [[InlineKeyboardButton(start_button_text[user_lang], callback_data="start_survey")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        GREETINGS[user_lang],
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    return Q1

async def start_survey_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинаем собственно опрос после нажатия кнопки"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_lang = context.user_data.get('language', 'ru')
    context.user_data['survey_started'] = True
    
    # Показываем первый вопрос
    await query.edit_message_text(
        QUESTIONS[user_lang][0],
        reply_markup=get_navigation_keyboard(0, user_lang)
    )
    
    return Q1

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    state = context.user_data.get('state', 0)
    answer = update.message.text.strip()
    
    # Проверяем, начат ли опрос
    if not context.user_data.get('survey_started', False):
        # Если опрос не начат, используем умные ответы
        await handle_general_message(update, context)
        return ConversationHandler.END
    
    user_lang = context.user_data.get('language', 'ru')
    
    # Проверяем валидность ответа ПЕРЕД определением языка
    is_valid, error_type = is_valid_answer(answer)
    if not is_valid:
        error_messages = {
            'ru': {
                'too_short': "❌ Пожалуйста, дайте более развёрнутый ответ (минимум 3 слова).\n\n💡 Пример хорошего ответа: \"Я считаю себя целеустремленным человеком, который всегда доводит дела до конца\"",
                'too_short_chars': "❌ Ответ слишком короткий. Напишите минимум 10 символов.\n\n💡 Постарайтесь раскрыть свои мысли подробнее",
                'meaningless': "❌ Пожалуйста, дайте осмысленный ответ.\n\n💡 Опишите свои мысли, чувства или опыт по данному вопросу",
                'empty': "❌ Вы не написали ответ. Пожалуйста, ответьте на вопрос."
            },
            'he': {
                'too_short': "❌ אנא תנו תשובה מפורטת יותר (מינימום 3 מילים).\n\n💡 דוגמה לתשובה טובה: \"אני רואה את עצמי כאדם נחוש שתמיד מביא דברים לסיום\"",
                'too_short_chars': "❌ התשובה קצרה מדי. כתבו לפחות 10 תווים.\n\n💡 נסו לפרט את המחשבות שלכם יותר",
                'meaningless': "❌ אנא תנו תשובה משמעותית.\n\n💡 תארו את המחשבות, הרגשות או הניסיון שלכם בנושא זה",
                'empty': "❌ לא כתבתם תשובה. אנא ענו על השאלה."
            },
            'en': {
                'too_short': "❌ Please provide a more detailed answer (minimum 3 words).\n\n💡 Example of good answer: \"I consider myself a determined person who always sees things through\"",
                'too_short_chars': "❌ Answer is too short. Write at least 10 characters.\n\n💡 Try to elaborate on your thoughts more",
                'meaningless': "❌ Please provide a meaningful answer.\n\n💡 Describe your thoughts, feelings or experience on this topic",
                'empty': "❌ You didn't write an answer. Please respond to the question."
            }
        }
        
        await update.message.reply_text(
            error_messages[user_lang].get(error_type, error_messages[user_lang]['too_short']),
            reply_markup=get_navigation_keyboard(state, user_lang)
        )
        return state  # Остаемся на том же вопросе
    
    # Определяем язык ТОЛЬКО по валидному ответу, если еще не определен
    if not context.user_data.get('language_detected', False):
        detected_lang = detect_language(answer)
        context.user_data['language'] = detected_lang
        context.user_data['language_detected'] = True
        user_lang = detected_lang  # Обновляем текущий язык
        if user.id in user_data:
            user_data[user.id]['language'] = detected_lang
    
    if user.id not in user_data:
        user_data[user.id] = {'answers': [None] * 7, 'language': user_lang}
    
    # Сохраняем ответ
    user_data[user.id]['answers'][state] = answer
    
    if state < 6:
        next_state = state + 1
        context.user_data['state'] = next_state
        await update.message.reply_text(
            QUESTIONS[user_lang][next_state],
            reply_markup=get_navigation_keyboard(next_state, user_lang)
        )
        return next_state
    else:
        # Все ответы собраны
        processing_messages = {
            'ru': "🔄 Анализирую ваши ответы... Это займёт несколько секунд.",
            'he': "🔄 מנתח את התשובות שלכם... זה ייקח כמה שניות.",
            'en': "🔄 Analyzing your answers... This will take a few seconds."
        }
        await update.message.reply_text(processing_messages[user_lang])
        await process_analysis(update, context)
        return ConversationHandler.END

async def handle_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка кнопки 'Назад'"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_lang = context.user_data.get('language', 'ru')
    
    # Извлекаем номер вопроса из callback_data
    target_question = int(query.data.split('_')[1])
    context.user_data['state'] = target_question
    
    # Показываем вопрос для редактирования
    back_messages = {
        'ru': f"⬅️ Вы вернулись к вопросу {target_question + 1}. Дайте новый ответ:",
        'he': f"⬅️ חזרתם לשאלה {target_question + 1}. תנו תשובה חדשה:",
        'en': f"⬅️ You returned to question {target_question + 1}. Give a new answer:"
    }
    
    await query.edit_message_text(
        f"{back_messages[user_lang]}\n\n{QUESTIONS[user_lang][target_question]}",
        reply_markup=get_navigation_keyboard(target_question, user_lang)
    )
    
    return target_question

async def process_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_lang = context.user_data.get('language', 'ru')
    answers = user_data.get(user.id, {}).get('answers', [])
    
    # Проверяем, что все ответы заполнены
    if None in answers or len(answers) != 7:
        error_msg = {
            'ru': "❌ Ошибка: не все ответы получены. Попробуйте начать заново с /start",
            'he': "❌ שגיאה: לא כל התשובות התקבלו. נסו להתחיל מחדש עם /start",
            'en': "❌ Error: not all answers received. Try starting over with /start"
        }
        await update.message.reply_text(error_msg[user_lang])
        return
    
    # Анализ стиля речи
    all_text = " ".join(answers)
    speech_analysis = analyze_speech_style(all_text, user_lang)
    
    answers_block = "\n".join(f"{i+1}) {q}\nОтвет: {a}\n" for i, (q, a) in enumerate(zip(QUESTIONS[user_lang], answers)))
    
    prompt = create_analysis_prompt(answers_block, speech_analysis, user_lang)
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.7,
            timeout=120
        )
        analysis = response.choices[0].message.content.strip()
        
        # Проверяем на неполный анализ
        if not analysis or len(analysis) < 500:
            error_msg = {
                'ru': "❌ Получен неполный анализ. Попробуйте еще раз через /start",
                'he': "❌ התקבל ניתוח חלקי. נסו שוב דרך /start", 
                'en': "❌ Incomplete analysis received. Try again via /start"
            }
            await update.message.reply_text(error_msg[user_lang])
            return
        
        # Дополняем анализ если он обрывается
        if not analysis.endswith('---') and '🔮 ПРОГНОЗ ПОВЕДЕНИЯ:' in analysis and not 'В отношениях:' in analysis:
            analysis += "\n\n[Анализ был автоматически дополнен для обеспечения полноты]"
        
        # Отправляем админу полный анализ (с ответами и анализом речи)
        admin_text = f"👤 Пользователь: {user.full_name} (ID: {user.id})\n🌐 Язык: {user_lang}\n\n📝 ОТВЕТЫ:\n{answers_block}\n\n{speech_analysis}\n\n🧠 ПОЛНЫЙ АНАЛИЗ:\n{analysis}"
        
        # Отправляем админу только если это не сам админ
        if user.id != ADMIN_CHAT_ID:
            try:
                # Разбиваем сообщение для админа на части если нужно
                max_length = 4000
                if len(admin_text) > max_length:
                    admin_parts = []
                    current_part = ""
                    lines = admin_text.split('\n')
                    
                    for line in lines:
                        if len(current_part + line + '\n') > max_length:
                            if current_part:
                                admin_parts.append(current_part.strip())
                                current_part = line + '\n'
                            else:
                                admin_parts.append(line[:max_length])
                                current_part = line[max_length:] + '\n'
                        else:
                            current_part += line + '\n'
                    
                    if current_part.strip():
                        admin_parts.append(current_part.strip())
                    
                    for i, part in enumerate(admin_parts):
                        if i == 0:
                            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=part)
                        else:
                            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"📋 Часть {i+1}/{len(admin_parts)}:\n\n{part}")
                else:
                    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
            except Exception as e:
                logger.error(f"Ошибка отправки админу: {e}")
        else:
            # Для админа добавляем специальное сообщение
            logger.info(f"Админ {user.full_name} (ID: {user.id}) прошел опрос. Детали не отправлены чтобы избежать дублирования.")
        
        # Отправляем пользователю только анализ (БЕЗ ответов)
        user_summary = extract_user_summary(analysis, user_lang)
        
        # Разбиваем длинный анализ на части
        max_length = 3800  # Еще меньше лимита для заголовков и безопасности
        if len(user_summary) > max_length:
            parts = []
            current_part = ""
            lines = user_summary.split('\n')
            
            for line in lines:
                if len(current_part + line + '\n') > max_length:
                    if current_part:
                        parts.append(current_part.strip())
                        current_part = line + '\n'
                    else:
                        # Если одна строка слишком длинная, разбиваем по символам
                        parts.append(line[:max_length])
                        current_part = line[max_length:] + '\n'
                else:
                    current_part += line + '\n'
            
            if current_part.strip():
                parts.append(current_part.strip())
            
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text(f"📋 **Продолжение анализа ({i+1}/{len(parts)}):**\n\n{part}", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(user_summary, parse_mode=ParseMode.MARKDOWN)
        
        # Отправляем сообщение о завершении
        completion_messages = {
            'ru': "✅ Анализ завершён! Все ваши данные удалены из системы для обеспечения конфиденциальности.\n\nДля нового анализа используйте /start",
            'he': "✅ הניתוח הושלם! כל הנתונים שלכם נמחקו מהמערכת להבטחת הסודיות.\n\nלניתוח חדש השתמשו ב-/start",
            'en': "✅ Analysis completed! All your data has been deleted from the system to ensure confidentiality.\n\nFor a new analysis use /start"
        }
        await update.message.reply_text(completion_messages[user_lang])
        
    except Exception as e:
        logger.error(f"Ошибка анализа: {e}")
        
        # Детальная диагностика ошибки
        if "timeout" in str(e).lower():
            error_msg = {
                'ru': "⏱️ Превышено время ожидания анализа. Попробуйте через несколько минут с /start",
                'he': "⏱️ זמן הניתוח חרג. נסו שוב בעוד מספר דקות עם /start",
                'en': "⏱️ Analysis timeout. Try again in a few minutes with /start"
            }
        elif "rate_limit" in str(e).lower() or "quota" in str(e).lower():
            error_msg = {
                'ru': "💰 Превышен лимит запросов к ИИ. Попробуйте позже с /start",
                'he': "💰 חרגנו ממכסת הבקשות לבינה מלאכותית. נסו מאוחר יותר עם /start",
                'en': "💰 AI request limit exceeded. Try later with /start"
            }
        else:
            error_msg = {
                'ru': "❌ Ошибка анализа. Попробуйте позже с /start",
                'he': "❌ שגיאת ניתוח. נסו שוב מאוחר יותר עם /start",
                'en': "❌ Analysis error. Try again later with /start"
            }
        
        await update.message.reply_text(error_msg[user_lang])
    finally:
        # Полностью очищаем данные пользователя
        secure_cleanup_user_data(user.id, context)

def analyze_speech_style(text, language):
    """Анализ стиля речи"""
    words = text.split()
    sentences = [s for s in text.split('.') if s.strip()]
    
    analysis = {
        'word_count': len(words),
        'sentence_count': len(sentences),
        'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0,
        'complexity': 'высокая' if len(words) > 200 else 'средняя' if len(words) > 100 else 'низкая',
        'emotional_markers': len(re.findall(r'[!?]{1,3}', text)),
        'personal_pronouns': 0
    }
    
    # Подсчет местоимений в зависимости от языка
    if language == 'ru':
        analysis['personal_pronouns'] = len(re.findall(r'\b(я|мне|мой|моя|мои|меня|мной)\b', text.lower()))
    elif language == 'he':
        analysis['personal_pronouns'] = len(re.findall(r'\b(אני|שלי|של|אותי)\b', text))
    else:  # en
        analysis['personal_pronouns'] = len(re.findall(r'\b(i|me|my|mine|myself)\b', text.lower()))
    
    if language == 'ru':
        style_description = f"""📊 Анализ речи:
• Объём текста: {analysis['word_count']} слов
• Сложность речи: {analysis['complexity']}
• Эмоциональность: {'высокая' if analysis['emotional_markers'] > 5 else 'умеренная'}
• Самофокусированность: {'высокая' if analysis['personal_pronouns'] > 10 else 'умеренная'}"""
    elif language == 'he':
        style_description = f"""📊 ניתוח דיבור:
• נפח טקסט: {analysis['word_count']} מילים
• מורכבות דיבור: {analysis['complexity']}
• רגשיות: {'גבוהה' if analysis['emotional_markers'] > 5 else 'בינונית'}
• מיקוד עצמי: {'גבוה' if analysis['personal_pronouns'] > 10 else 'בינוני'}"""
    else:  # en
        style_description = f"""📊 Speech analysis:
• Text volume: {analysis['word_count']} words
• Speech complexity: {analysis['complexity']}
• Emotionality: {'high' if analysis['emotional_markers'] > 5 else 'moderate'}
• Self-focus: {'high' if analysis['personal_pronouns'] > 10 else 'moderate'}"""
    
    return style_description

def create_analysis_prompt(answers_block, speech_analysis, language):
    """Создание промпта для анализа"""
    if language == 'ru':
        return f"""Ты — ведущий психолог-профайлер с 20-летним опытом, доктор психологических наук, специалист по психоанализу (Фрейд, Юнг), когнитивно-поведенческой терапии, криминальному профайлингу и лингвистическому анализу.

Проведи ГЛУБОКИЙ профессиональный анализ личности по методикам:
• Психоанализ (Фрейд): структура личности, защитные механизмы
• Аналитическая психология (Юнг): архетипы, типология
• Теория Большой Пятёрки (OCEAN)
• Типология Майерс-Бриггс (MBTI)
• Лингвистический профайлинг

ТАКЖЕ проанализируй стиль речи пользователя:

КРИТИЧЕСКИ ВАЖНО: Обязательно включи детальные профессиональные рекомендации:
💼 Анализируй когнитивные способности, эмоциональный интеллект, мотивацию
💼 Определи оптимальные сферы деятельности исходя из типа личности
💼 Укажи конкретные профессии с психологическим обоснованием
💼 Предложи направления обучения и развития навыков
💼 Разработай стратегию карьерного роста

ОБЯЗАТЕЛЬНЫЙ ФОРМАТ ОТВЕТА:
---
🧠 ПСИХОАНАЛИТИЧЕСКИЙ ПРОФИЛЬ:
Структура личности: [доминирующая инстанция: Ид/Эго/Суперэго + обоснование]
Защитные механизмы: [2-3 основных механизма с примерами из ответов]
Бессознательные конфликты: [выявленные внутренние противоречия]

🎭 АРХЕТИП И ТИПОЛОГИЯ:
Доминирующий архетип: [архетип по Юнгу + описание]
MBTI тип: [4-буквенный код + расшифровка]
Темперамент: [тип + психофизиологическое обоснование]

📊 ПРОФИЛЬ ЛИЧНОСТИ (Big Five):
Открытость: [балл 1-10 + описание]
Добросовестность: [балл 1-10 + описание]  
Экстраверсия: [балл 1-10 + описание]
Доброжелательность: [балл 1-10 + описание]
Нейротизм: [балл 1-10 + описание]

🎯 ПОВЕДЕНЧЕСКИЙ ПРОФАЙЛИНГ:
Мотивационная структура: [основные драйверы поведения]
Стратегии совладания: [как справляется со стрессом]
Модель принятия решений: [рациональная/интуитивная/эмоциональная]
Межличностный стиль: [паттерны взаимодействия]

🗣️ ЛИНГВИСТИЧЕСКИЙ АНАЛИЗ:
Речевые паттерны: [особенности языка и стиля]
Когнитивные маркеры: [способ мышления через речь]
Эмоциональные индикаторы: [эмоциональное состояние через язык]

⚠️ ПСИХОЛОГИЧЕСКИЕ РИСКИ:
[2-3 потенциальные проблемные области]

🎯 РЕКОМЕНДАЦИИ ПО РАЗВИТИЮ:
[3-4 конкретные рекомендации с обоснованием]

💼 ПРОФЕССИОНАЛЬНЫЕ РЕКОМЕНДАЦИИ:
Подходящие сферы деятельности: [на основе типа личности, способностей и мотивации]
Конкретные профессии: [3-5 наиболее подходящих профессий с психологическим обоснованием]
Направления обучения: [курсы, специальности, навыки для развития карьеры]
Карьерная стратегия: [оптимальные пути профессионального роста и развития]

🔮 ПРОГНОЗ ПОВЕДЕНИЯ:
В стрессе: [вероятные реакции]
В команде: [роль и поведение]
В отношениях: [паттерны взаимодействия]
---

ОТВЕТЫ ДЛЯ АНАЛИЗА:
{answers_block}

Проведи максимально глубокий анализ, используя профессиональную терминологию и конкретные примеры из ответов."""

    elif language == 'he':
        return f"""אתה פסיכולוג-פרופיילר מוביל עם 20 שנות ניסיון, דוקטור לפסיכולוגיה, מומחה בפסיכואנליזה (פרויד, יונג), טיפול קוגניטיבי-התנהגותי, פרופיילינג פלילי וניתוח לשוני.

בצע ניתוח מקצועי עמוק של האישיות לפי השיטות:
• פסיכואנליזה (פרויד): מבנה האישיות, מנגנוני הגנה
• פסיכולוגיה אנליטית (יונג): ארכיטיפים, טיפולוגיה
• תיאוריית החמישייה הגדולה (OCEAN)
• טיפולוגיית מאיירס-בריגס (MBTI)
• פרופיילינג לשוני

גם נתח את סגנון הדיבור של המשתמש:

חשוב מאוד: כלול המלצות מקצועיות מפורטות:
💼 תחומי עבודה מתאימים על בסיס סוג האישיות והיכולות
💼 מקצועות ספציפיים (3-5) עם הנמקה פסיכולוגית
💼 כיווני לימוד והשתלמויות מומלצים
💼 אסטרטגיית קריירה אופטימלית לפיתוח מקצועי

פורמט חובה לתשובה:
---
🧠 פרופיל פסיכואנליטי:
מבנה האישיות: [אינסטנציה דומיננטית: אידו/אגו/סופר-אגו + הנמקה]
מנגנוני הגנה: [2-3 מנגנונים עיקריים עם דוגמאות מהתשובות]
קונפליקטים לא מודעים: [סתירות פנימיות שזוהו]

🎭 ארכיטיפ וטיפולוגיה:
ארכיטיפ דומיננטי: [ארכיטיפ לפי יונג + תיאור]
סוג MBTI: [קוד 4 אותיות + הסבר]
טמפרמנט: [סוג + הנמקה פסיכופיזיולוגית]

📊 פרופיל אישיות (Big Five):
פתיחות: [ציון 1-10 + תיאור]
מצפוניות: [ציון 1-10 + תיאור]
אקסטרוורסיה: [ציון 1-10 + תיאור]
נעימות: [ציון 1-10 + תיאור]
נוירוטיות: [ציון 1-10 + תיאור]

🎯 פרופיילינג התנהגותי:
מבנה מוטיבציוני: [מניעים עיקריים להתנהגות]
אסטרטגיות התמודדות: [איך מתמודד עם לחץ]
מודל קבלת החלטות: [רציונלי/אינטואיטיבי/רגשי]
סגנון בינאישי: [דפוסי אינטראקציה]

🗣️ ניתוח לשוני:
דפוסי דיבור: [מאפייני שפה וסגנון]
סמנים קוגניטיביים: [דרך חשיבה דרך הדיבור]
אינדיקטורים רגשיים: [מצב רגשי דרך השפה]

⚠️ סיכונים פסיכולוגיים:
[2-3 אזורים בעייתיים פוטנציאליים]

🎯 המלצות לפיתוח:
[3-4 המלצות קונקרטיות עם הנמקה]

💼 המלצות מקצועיות:
תחומי פעילות מתאימים: [על בסיס סוג אישיות, יכולות ומוטיבציה]
מקצועות קונקרטיים: [3-5 המקצועות המתאימים ביותר עם הנמקה פסיכולוגית]
כיווני לימוד: [קורסים, התמחויות, כישורים לפיתוח קריירה]
אסטרטגיית קריירה: [דרכים אופטימליות לצמיחה ופיתוח מקצועי]

🔮 תחזית התנהגות:
בלחץ: [תגובות סבירות]
בצוות: [תפקיד והתנהגות]
ביחסים: [דפוסי אינטראקציה]
---

תשובות לניתוח:
{answers_block}

בצע ניתוח עמוק ביותר, השתמש בטרמינולוגיה מקצועית ובדוגמאות קונקרטיות מהתשובות."""

    else:  # English
        return f"""You are a leading psychologist-profiler with 20 years of experience, PhD in Psychology, specialist in psychoanalysis (Freud, Jung), cognitive-behavioral therapy, criminal profiling, and linguistic analysis.

Conduct a DEEP professional personality analysis using methods:
• Psychoanalysis (Freud): personality structure, defense mechanisms
• Analytical psychology (Jung): archetypes, typology
• Big Five theory (OCEAN)
• Myers-Briggs typology (MBTI)
• Linguistic profiling

ALSO analyze the user's speech style:

CRITICAL: Include detailed professional recommendations:
💼 Suitable career fields based on personality type and abilities
💼 Specific professions (3-5) with psychological justification
💼 Learning directions and recommended training/education
💼 Optimal career strategy for professional development

MANDATORY RESPONSE FORMAT:
---
🧠 PSYCHOANALYTIC PROFILE:
Personality structure: [dominant instance: Id/Ego/Superego + justification]
Defense mechanisms: [2-3 main mechanisms with examples from answers]
Unconscious conflicts: [identified internal contradictions]

🎭 ARCHETYPE AND TYPOLOGY:
Dominant archetype: [Jung archetype + description]
MBTI type: [4-letter code + explanation]
Temperament: [type + psychophysiological justification]

📊 PERSONALITY PROFILE (Big Five):
Openness: [score 1-10 + description]
Conscientiousness: [score 1-10 + description]
Extraversion: [score 1-10 + description]
Agreeableness: [score 1-10 + description]
Neuroticism: [score 1-10 + description]

🎯 BEHAVIORAL PROFILING:
Motivational structure: [main behavioral drivers]
Coping strategies: [how handles stress]
Decision-making model: [rational/intuitive/emotional]
Interpersonal style: [interaction patterns]

🗣️ LINGUISTIC ANALYSIS:
Speech patterns: [language and style features]
Cognitive markers: [thinking style through speech]
Emotional indicators: [emotional state through language]

⚠️ PSYCHOLOGICAL RISKS:
[2-3 potential problem areas]

🎯 DEVELOPMENT RECOMMENDATIONS:
[3-4 concrete recommendations with justification]

💼 PROFESSIONAL RECOMMENDATIONS:
Suitable activity fields: [based on personality type, abilities and motivation]
Specific professions: [3-5 most suitable professions with psychological justification]
Learning directions: [courses, specializations, skills for career development]
Career strategy: [optimal paths for professional growth and development]

🔮 BEHAVIOR FORECAST:
Under stress: [probable reactions]
In team: [role and behavior]
In relationships: [interaction patterns]
---

ANSWERS FOR ANALYSIS:
{answers_block}

Conduct the deepest possible analysis using professional terminology and specific examples from the answers."""

def extract_user_summary(analysis, language):
    """Извлекает краткую версию анализа для пользователя (без личных данных)"""
    if language == 'ru':
        header = "🔬 **Ваш психологический профиль:**\n\n"
        footer = "\n\n🔒 **Конфиденциальность:** Ваши ответы удалены из системы для обеспечения безопасности."
    elif language == 'he':
        header = "🔬 **הפרופיל הפסיכולוגי שלכם:**\n\n"
        footer = "\n\n🔒 **סודיות:** התשובות שלכם נמחקו מהמערכת להבטחת האבטחה."
    else:  # en
        header = "🔬 **Your psychological profile:**\n\n"
        footer = "\n\n🔒 **Confidentiality:** Your answers have been deleted from the system for security."
    
    return f"{header}{analysis}{footer}"

def secure_cleanup_user_data(user_id, context):
    """Безопасная очистка всех данных пользователя"""
    try:
        # Удаляем из глобального хранилища
        if user_id in user_data:
            user_data.pop(user_id, None)
        
        # Очищаем контекст пользователя
        context.user_data.clear()
        
        # Записываем в лог факт удаления данных
        logger.info(f"Все данные пользователя {user_id} безопасно удалены для обеспечения конфиденциальности")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке данных пользователя {user_id}: {e}")

async def delete_user_messages(context, user_id):
    """Удаление сообщений пользователя для конфиденциальности (устаревшая функция)"""
    # Эта функция заменена на secure_cleanup_user_data
    pass

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_lang = context.user_data.get('language', 'ru')
    
    cancel_msg = {
        'ru': '❌ Опрос отменён. Все данные удалены. Для нового анализа напишите /start',
        'he': '❌ הסקר בוטל. כל הנתונים נמחקו. לניתוח חדש כתבו /start',
        'en': '❌ Survey cancelled. All data deleted. For new analysis type /start'
    }
    
    await update.message.reply_text(cancel_msg[user_lang])
    
    # Безопасно очищаем данные
    secure_cleanup_user_data(user.id, context)
    return ConversationHandler.END

async def setup_bot_commands(application):
    """Настройка команд бота"""
    commands = [
        BotCommand("start", "Начать психологический анализ"),
        BotCommand("help", "Справка о возможностях бота"),
        BotCommand("cancel", "Отменить текущий опрос")
    ]
    await application.bot.set_my_commands(commands)

def main():
    print("🚀 Запуск профессионального психоаналитического бота...")
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Q1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$"),
                CallbackQueryHandler(start_survey_callback, pattern="start_survey")
            ],
            Q2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q3: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q4: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q5: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q6: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q7: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    
    # Обработчик для всех остальных сообщений (вне опроса)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message))
    
    # Устанавливаем команды бота после инициализации
    async def post_init(application):
        await setup_bot_commands(application)
    
    application.post_init = post_init
    
    print("✅ Бот запущен. Для остановки нажмите Ctrl+C.")
    
    # Запускаем polling без JobQueue
    application.run_polling(
        allowed_updates=['message', 'callback_query'],
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main() 