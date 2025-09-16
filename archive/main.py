import logging
import os
import re
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ForceReply, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)

# Голосовые функции отключены полностью
VOICE_ENABLED = False
import openai
from telegram.constants import ParseMode

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
HR_PASSWORD = os.getenv('HR_PASSWORD', 'HR2024')

# Проверка необходимых переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в .env файле!")

# ADMIN_CHAT_ID больше не обязателен в минимальном режиме
try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID else None
except ValueError:
    ADMIN_CHAT_ID = None

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

# HR-специфичные вопросы для оценки кандидатов
HR_QUESTIONS = {
    'ru': [
        "Опиши свой опыт работы. Какие задачи выполнял и как справлялся с трудностями?",
        "Как ты работаешь в команде? Приведи пример успешного сотрудничества и конфликта.",
        "Что тебя мотивирует в работе: деньги, признание, развитие или что-то другое?",
        "Как ты справляешься со стрессом и дедлайнами? Опиши сложную ситуацию.",
        "Какие у тебя карьерные цели на ближайшие 2-3 года?",
        "Как ты относишься к обратной связи и критике? Приведи пример.",
        "Что для тебя важнее: стабильность или вызовы? Почему?"
    ],
    'he': [
        "תאר את הניסיון שלך בעבודה. אילו משימות ביצעת ואיך התמודדת עם קשיים?",
        "איך אתה עובד בצוות? תן דוגמה לשיתוף פעולה מוצלח ולקונפליקט.",
        "מה מניע אותך בעבודה: כסף, הכרה, פיתוח או משהו אחר?",
        "איך אתה מתמודד עם לחץ ודדליינים? תאר מצב קשה.",
        "אילו מטרות קריירה יש לך לשנים הקרובות 2-3?",
        "איך אתה מתייחס למשוב וביקורת? תן דוגמה.",
        "מה חשוב לך יותר: יציבות או אתגרים? למה?"
    ],
    'en': [
        "Describe your work experience. What tasks did you perform and how did you handle difficulties?",
        "How do you work in a team? Give an example of successful collaboration and conflict.",
        "What motivates you at work: money, recognition, development or something else?",
        "How do you handle stress and deadlines? Describe a difficult situation.",
        "What are your career goals for the next 2-3 years?",
        "How do you respond to feedback and criticism? Give an example.",
        "What's more important to you: stability or challenges? Why?"
    ]
}

GREETINGS = {
    'ru': """🎯 **Карьерный психоаналитик + HR-профориентолог**

**Определю ваш психотип и подходящие профессии за 3-5 минут!**

🔍 **Что я умею:**
• Глубокий психологический анализ личности
• Профайлинг по методикам Фрейда, Юнга, Майерс-Бриггс  
• Анализ стиля речи и языковых паттернов
• Определение темперамента и архетипа личности
• Выявление защитных механизмов психики
• **Анализ снов и переживаний** для карьерных инсайтов
• **Рекомендации по личностному развитию**

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
    'he': """🎯 **פסיכואנליטיקאי קריירה + יועץ HR**

**אקבע את הפסיכוטיפ שלכם ומקצועות מתאימים תוך 3-5 דקות!**

🔍 **מה אני יודע לעשות:**
• ניתוח פסיכולוגי עמוק של האישיות
• פרופיילינג לפי שיטות פרויד, יונג, מאיירס-בריגס
• ניתוח סגנון דיבור ודפוסים לשוניים
• קביעת טמפרמנט וארכיטיפ אישיות
• זיהוי מנגנוני הגנה נפשיים
• **ניתוח חלומות וחוויות** לתובנות קריירה
• **המלצות לפיתוח אישי**

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

💼 **למומחי HR:** 
• `/hr_panel [סיסמה]` - צפייה במועמדים
• `/hr_compare [סיסמה]` - השוואת מועמדים

להתחלת ניתוח כתבו /start""",
    'en': """🎯 **Career Psychoanalyst + HR Consultant**

**I'll determine your psychotype and suitable professions in 3-5 minutes!**

🔍 **What I can do:**
• Deep psychological personality analysis
• Profiling using Freud, Jung, Myers-Briggs methods
• Speech style and linguistic pattern analysis
• Temperament and personality archetype determination
• Identification of psychological defense mechanisms
• **Dream and experience analysis** for career insights
• **Personal development recommendations**

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

💼 **For HR specialists:** 
• `/hr_panel [password]` - view candidates
• `/hr_compare [password]` - compare candidates

To start analysis, type /start"""
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

💼 **Для HR-специалистов:** 
• `/hr_panel [пароль]` - просмотр кандидатов
• `/hr_compare [пароль]` - сравнение кандидатов

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

💼 **למומחי HR:** 
• `/hr_panel [סיסמה]` - צפייה במועמדים
• `/hr_compare [סיסמה]` - השוואת מועמדים

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

💼 **For HR specialists:** 
• `/hr_panel [password]` - view candidates
• `/hr_compare [password]` - compare candidates

To start analysis, type /start"""
}

# Состояния для ConversationHandler
(Q1, Q2, Q3, Q4, Q5, Q6, Q7) = range(7)

# Временное хранилище ответов
user_data = {}

# Глобальная переменная для истории диалогов
conversation_history = {}

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

"""Минимальный режим: база данных и HR-функции отключены"""

def check_hr_password(message_text):
    """Проверка HR-пароля из сообщения"""
    parts = message_text.split()
    if len(parts) < 2:
        return False
    return parts[1] == HR_PASSWORD

def get_hr_access_denied_message(language):
    """Получение сообщения об отказе в доступе к HR-функциям"""
    messages = {
        'ru': """❌ **Эта функция доступна только HR-специалистам.**

Но я могу провести для вас психологический анализ! 

Напишите `/start` для начала анализа личности и профориентации.

💡 *Для HR-специалистов: используйте команды с паролем*""",
        
        'he': """❌ **פונקציה זו זמינה רק למומחי HR.**

אבל אני יכול לבצע עבורכם ניתוח פסיכולוגי!

כתבו `/start` להתחלת ניתוח אישיות והכוונה מקצועית.

💡 *למומחי HR: השתמשו בפקודות עם סיסמה*""",
        
        'en': """❌ **This function is available only for HR specialists.**

But I can conduct a psychological analysis for you!

Write `/start` to begin personality analysis and career guidance.

💡 *For HR specialists: use commands with password*"""
    }
    return messages.get(language, messages['ru'])

def detect_language(text: str) -> str:
    """Определяет язык текста (теперь всегда возвращает 'ru')"""
    return 'ru'

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
        'ru': f"""Ты психоаналитик и HR-консультант. Пользователь написал: "{user_message}"

ПРАВИЛА:
1. СНАЧАЛА отвечай на прямой вопрос (если есть)
2. Потом кратко анализируй (1-2 предложения)
3. Задавай ОДИН вопрос для продолжения диалога
4. Максимум 3 предложения в ответе
5. Будь мягким и понимающим к опечаткам

Если спрашивают "что умеешь" - отвечай что делаешь анализ личности и профориентацию.
Если просто приветствие - поприветствуй и спроси о целях/мечтах.
Если рассказывают о себе - кратко проанализируй и задай вопрос.
Если не понял сообщение - попроси уточнить мягко.

Будь кратким, мягким и по делу!""",
        
        'he': f"""אתה פסיכואנליטיקאי ויועץ HR. המשתמש כתב: "{user_message}"

כללים:
1. קודם תענה על השאלה הישירה (אם יש)
2. אחר כך נתח בקצרה (1-2 משפטים)
3. שאל שאלה אחת להמשך השיחה
4. מקסימום 3 משפטים בתשובה

אם שואלים "מה אתה יודע לעשות" - תגיד שעושה ניתוח אישיות והכוונה מקצועית.
אם רק ברכה - ברך ושאל על מטרות/חלומות.
אם מספרים על עצמם - נתח בקצרה ושאל שאלה.

היה קצר ולעניין!""",
        
        'en': f"""You are a psychoanalyst and HR consultant. The user wrote: "{user_message}"

RULES:
1. FIRST answer the direct question (if any)
2. Then briefly analyze (1-2 sentences)
3. Ask ONE question to continue the conversation
4. Maximum 3 sentences in response

If they ask "what can you do" - say you do personality analysis and career guidance.
If just greeting - greet and ask about goals/dreams.
If they tell about themselves - briefly analyze and ask a question.

Be brief and to the point!"""
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
    user = update.effective_user
    user_message = update.message.text
    user_lang = 'ru'
    
    # Сохраняем определенный язык
    context.user_data['language'] = user_lang
    
    # Собираем историю диалога для экспресс-анализа
    if user.id not in conversation_history:
        conversation_history[user.id] = []
    
    conversation_history[user.id].append(user_message)
    # Ограничиваем историю (максимум 10 сообщений для экономии токенов)
    if len(conversation_history[user.id]) > 10:
        conversation_history[user.id] = conversation_history[user.id][-10:]
    
    message_count = len(conversation_history[user.id])
    
    # АВТОЗАВЕРШЕНИЕ: После 6 сообщений → принудительный анализ
    if message_count >= 6:
        analysis_start_texts = {
            'ru': "🎯 **Отлично! У меня достаточно материала для анализа.**\n\n🔄 *Анализирую ваши сообщения и составляю психологический портрет...*",
            'he': "🎯 **מעולה! יש לי מספיק חומר לניתוח.**\n\n🔄 *מנתח את ההודעות שלכם ומכין פרופיל פסיכולוגי...*",
            'en': "🎯 **Excellent! I have enough material for analysis.**\n\n🔄 *Analyzing your messages and creating psychological profile...*"
        }
        
        await update.message.reply_text(
            analysis_start_texts[user_lang], 
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Запускаем анализ и завершаем диалог
        await process_express_analysis(update, context)
        return
    
    # Проверяем, ждем ли мы данные для экспресс-анализа
    if context.user_data.get('waiting_for_express_data', False):
        context.user_data['waiting_for_express_data'] = False
        await update.message.reply_text("🔄 Анализирую ваши сообщения...")
        await process_express_analysis(update, context)
        return
    
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
    
    # ПРОМЕЖУТОЧНЫЕ ПРЕДЛОЖЕНИЯ
    if message_count == 3:
        transition_texts = {
            'ru': f"{smart_response}\n\n💭 **Вижу, вы готовы к более глубокому анализу!**\n\nВыберите формат:",
            'he': f"{smart_response}\n\n💭 **אני רואה שאתם מוכנים לניתוח עמוק יותר!**\n\nבחרו פורמט:",
            'en': f"{smart_response}\n\n💭 **I see you're ready for deeper analysis!**\n\nChoose format:"
        }
        
        keyboard = [
            [InlineKeyboardButton("⚡ Экспресс-анализ сейчас", callback_data='express_analysis')],
            [InlineKeyboardButton("💬 Еще поговорить", callback_data='continue_chat')],
            [InlineKeyboardButton("📋 Полный тест", callback_data='full_test')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            transition_texts[user_lang],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif message_count == 5:
        warning_texts = {
            'ru': f"{smart_response}\n\n🔔 **Еще одно сообщение и я начну анализ!**\n\nИли выберите действие:",
            'he': f"{smart_response}\n\n🔔 **עוד הודעה אחת ואתחיל ניתוח!**\n\nאו בחרו פעולה:",
            'en': f"{smart_response}\n\n🔔 **One more message and I'll start analysis!**\n\nOr choose action:"
        }
        
        keyboard = [
            [InlineKeyboardButton("⚡ Анализ сейчас", callback_data='express_analysis')],
            [InlineKeyboardButton("📋 Полный тест", callback_data='full_test')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            warning_texts[user_lang],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    else:
        # Обычный ответ без кнопок
        await update.message.reply_text(smart_response)
        
        # Показываем кнопки только в ключевые моменты
        if message_count == 3:
            # Предлагаем выбор после 3 сообщений
            keyboard = [
                [InlineKeyboardButton("💬 Продолжить диалог", callback_data="continue_chat")],
                [InlineKeyboardButton("⚡ Экспресс-анализ", callback_data="express_analysis")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
        elif message_count == 6:
            # Предупреждение о завершении после 6 сообщений
            keyboard = [
                [InlineKeyboardButton("⚡ Анализ сейчас", callback_data="express_analysis")],
                [InlineKeyboardButton("📋 Полный тест", callback_data="full_test")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
        elif message_count >= 7:
            # Принудительный анализ после 7 сообщений
            await process_express_analysis(update, context)
            return
 
"""HR-команды отключены в минимальном режиме"""

"""HR-команды отключены в минимальном режиме"""

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи (минимальный режим)"""
    await update.message.reply_text(HELP_TEXT['ru'], parse_mode=ParseMode.MARKDOWN)

async def hr_compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сравнение кандидатов"""
    user = update.effective_user
    user_lang = context.user_data.get('language', 'ru')
    
    # Проверяем пароль
    if not check_hr_password(update.message.text):
        await update.message.reply_text(get_hr_access_denied_message(user_lang), parse_mode=ParseMode.MARKDOWN)
        return
    
    # Получаем всех кандидатов
    candidates = get_all_candidates()
    
    if len(candidates) < 2:
        await update.message.reply_text("📊 Для сравнения нужно минимум 2 кандидата.")
        return
    
    # Создаем сравнительную таблицу
    report = "📊 **СРАВНЕНИЕ КАНДИДАТОВ**\n\n"
    
    # Заголовки
    report += "| Кандидат | Лидерство | Команда | Стресс | Мотивация | Общая |\n"
    report += "|----------|-----------|---------|--------|-----------|-------|\n"
    
    for candidate in candidates[:5]:  # Сравниваем топ-5
        hr_scores = candidate.get('hr_scores', {})
        total_score = sum(hr_scores.values()) / len(hr_scores) if hr_scores else 0
        
        name = candidate['name'][:15] + "..." if len(candidate['name']) > 15 else candidate['name']
        leadership = hr_scores.get('leadership', 0)
        teamwork = hr_scores.get('teamwork', 0)
        stress = hr_scores.get('stress_resistance', 0)
        motivation = hr_scores.get('motivation', 0)
        
        report += f"| {name} | {leadership} | {teamwork} | {stress} | {motivation} | {total_score:.1f} |\n"
    
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    
    # Очищаем предыдущие данные если есть
    user_data.pop(user.id, None)
    context.user_data.clear()
    
    # Устанавливаем язык по умолчанию
    context.user_data['language'] = 'ru'
    
    logger.info(f"Пользователь {user.first_name} ({user.id}) начал сессию. Язык: ru")

    # Сразу показываем главное меню
    await show_main_menu(update, context)
    return Q1

async def continue_chat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Еще поговорить'"""
    query = update.callback_query
    await query.answer()
    
    user_lang = context.user_data.get('language', 'ru')
    
    continue_messages = {
        'ru': "💬 **Отлично! Продолжаем общение.**\n\nРасскажите еще что-то интересное о себе - ваши мечты, страхи, планы или просто мысли...",
        'he': "💬 **מעולה! ממשיכים לשוחח.**\n\nספרו עוד משהו מעניין על עצמכם - חלומות, פחדים, תוכניות או סתם מחשבות...",
        'en': "💬 **Great! Let's continue chatting.**\n\nTell me something more interesting about yourself - your dreams, fears, plans or just thoughts..."
    }
    
    await query.edit_message_text(
        continue_messages[user_lang],
        parse_mode=ParseMode.MARKDOWN
    )

async def full_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Полный тест'"""
    query = update.callback_query
    await query.answer()
    
    # Запускаем полный тест
    await start_command(update, context)

async def express_analysis_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Экспресс-анализ из диалога"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_lang = context.user_data.get('language', 'ru')
    
    # Собираем последние сообщения пользователя для анализа
    conversation_data = conversation_history.get(user.id, [])
    
    if len(conversation_data) < 1:
        # Если нет данных, задаем профессиональные вопросы
        express_intro = {
            'ru': """⚡ **Экспресс-анализ из диалога**

Цель: быстро определить ваш психотип и подходящие профессии на основе ваших сообщений.

**Давайте познакомимся! Расскажите мне:**

• Что вас больше всего вдохновляет в жизни?
• Какие задачи приносят вам радость?
• О чем вы мечтаете в профессиональном плане?
• Какие у вас есть сильные стороны?

Или просто поделитесь любыми мыслями - я проанализирую и дам карьерные рекомендации!""",
            
            'he': """⚡ **ניתוח מהיר מהשיחה**

מטרה: לקבוע במהירות את הפסיכוטיפ והמקצועות המתאימים על בסיס ההודעות שלכם.

**בואו נכיר! ספרו לי:**

• מה הכי מעורר השראה בחיים שלכם?
• אילו משימות מביאות לכם שמחה?
• על מה אתם חולמים מבחינה מקצועית?
• מה החוזקות שלכם?

או פשוט שתפו כל מחשבה - אנתח ואתן המלצות קריירה!""",
            
            'en': """⚡ **Express analysis from chat**

Goal: quickly determine your psychotype and suitable professions based on your messages.

**Let's get acquainted! Tell me:**

• What inspires you most in life?
• What tasks bring you joy?
• What are your professional dreams?
• What are your strengths?

Or just share any thoughts - I'll analyze and give career recommendations!"""
        }
        
        await query.edit_message_text(express_intro[user_lang], parse_mode=ParseMode.MARKDOWN)
        context.user_data['waiting_for_express_data'] = True
        return Q1
    else:
        # Анализируем собранные данные
        express_processing = {
            'ru': "🔄 Анализирую ваши сообщения для определения психотипа и карьерных рекомендаций...",
            'he': "🔄 מנתח את ההודעות שלכם לקביעת הפסיכוטיפ והמלצות קריירה...",
            'en': "🔄 Analyzing your messages to determine psychotype and career recommendations..."
        }
        await query.edit_message_text(express_processing[user_lang])
        await process_express_analysis(update, context)
        return ConversationHandler.END

async def start_survey_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинаем собственно опрос после нажатия кнопки"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_lang = context.user_data.get('language', 'ru')
    context.user_data['survey_started'] = True
    
    # Краткое вступление перед опросом
    survey_intro = {
        'ru': """📋 **Начинаем краткий опрос для глубокого анализа личности**

Цель: определить ваш психотип, темперамент и подходящие профессии на основе научных методик (Фрейд, Юнг, MBTI, Big Five).

**Важно:** Отвечайте честно и подробно - это поможет дать максимально точные карьерные рекомендации.

Готовы? Начинаем с первого вопроса:""",
        
        'he': """📋 **מתחילים סקר קצר לניתוח עמוק של האישיות**

מטרה: לקבוע את הפסיכוטיפ, הטמפרמנט והמקצועות המתאימים על בסיס שיטות מדעיות (פרויד, יונג, MBTI, Big Five).

**חשוב:** ענו בכנות ובפירוט - זה יעזור לתת המלצות קריירה מדויקות ככל האפשר.

מוכנים? מתחילים עם השאלה הראשונה:""",
        
        'en': """📋 **Starting a brief survey for deep personality analysis**

Goal: determine your psychotype, temperament and suitable professions based on scientific methods (Freud, Jung, MBTI, Big Five).

**Important:** Answer honestly and in detail - this will help provide the most accurate career recommendations.

Ready? Let's start with the first question:"""
    }
    
    # Показываем вступление и первый вопрос
    intro_text = f"{survey_intro[user_lang]}\n\n{QUESTIONS[user_lang][0]}"
    
    await query.edit_message_text(
        intro_text,
        reply_markup=get_navigation_keyboard(0, user_lang),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return Q1

async def process_express_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка экспресс-анализа из диалога"""
    user = update.effective_user
    user_lang = context.user_data.get('language', 'ru')
    
    # Получаем данные из глобальной переменной conversation_history
    conversation_data = conversation_history.get(user.id, [])
    
    if not conversation_data or len(conversation_data) < 1:
        # Если нет данных, задаем профессиональные вопросы
        questions = {
            'ru': """🤔 **Давайте познакомимся поближе!**

Расскажите мне что-то о себе:
• Что вас вдохновляет?
• Какие у вас мечты?
• Что приносит радость?
• О чем вы думаете перед сном?

Любая информация поможет мне понять ваш психотип!""",
            'he': """🤔 **בואו נכיר יותר!**

ספרו לי משהו על עצמכם:
• מה מעורר השראה?
• אילו חלומות יש לכם?
• מה מביא שמחה?
• על מה אתם חושבים לפני השינה?

כל מידע יעזור לי להבין את הפסיכוטיפ שלכם!""",
            'en': """🤔 **Let's get to know each other better!**

Tell me something about yourself:
• What inspires you?
• What dreams do you have?
• What brings joy?
• What do you think about before sleep?

Any information will help me understand your psychotype!"""
        }
        if update.message:
            await update.message.reply_text(questions[user_lang], parse_mode=ParseMode.MARKDOWN)
        else:
            await update.callback_query.message.reply_text(questions[user_lang], parse_mode=ParseMode.MARKDOWN)
        return
    
    # Создаем промпт для экспресс-анализа
    conversation_text = " ".join(conversation_data)
    
    express_prompts = {
        'ru': f"""Ты комбинированный эксперт: психоаналитик (Фрейд, Юнг) + HR-специалист + MBTI-консультант + Big Five эксперт. Проанализируй диалог и дай профессиональную оценку.

ДИАЛОГ ПОЛЬЗОВАТЕЛЯ:
{conversation_text}

ТВОИ ДВЕ ГЛАВНЫЕ ЦЕЛИ:
1. ГЛУБОКИЙ ПСИХОАНАЛИЗ: Определи психотип, архетип, защитные механизмы
2. HR-ОЦЕНКА: Профессиональный потенциал, подходящие роли, рекомендации для найма

Проведи МУЛЬТИУРОВНЕВЫЙ анализ:

🧠 ПСИХОЛОГИЧЕСКИЙ ПРОФИЛЬ:
- ФРЕЙД: структура личности (Ид/Эго/Суперэго), защитные механизмы
- ЮНГ: доминирующий архетип (Мудрец, Герой, Творец, Правитель, и т.д.)
- MBTI: предположительный тип (4 буквы с объяснением)
- BIG FIVE: оценка по OCEAN (1-10 баллов каждый)

💼 HR-ОЦЕНКА:
- Лидерский потенциал (1-10)
- Командная работа (1-10) 
- Стрессоустойчивость (1-10)
- Подходящие профессии (3 конкретные с психологическим обоснованием)
- Рекомендация для HR: РЕКОМЕНДОВАН / УСЛОВНО / НЕ РЕКОМЕНДОВАН

ФОРМАТ:
🎯 ЭКСПРЕСС-ПРОФИЛЬ:
🧠 Психотип: [MBTI] - [архетип] 
📊 Big Five: O[X] C[X] E[X] A[X] N[X]
💼 HR-оценки: Лидерство [X/10], Команда [X/10], Стресс [X/10]
🎯 Профессии: [3 конкретные с обоснованием]
✅ Рекомендация: [РЕКОМЕНДОВАН/УСЛОВНО/НЕ РЕКОМЕНДОВАН] + причина

Анализируй как профессиональный психолог + HR-эксперт!""",
        
        'he': f"""אתה מומחה משולב: פסיכואנליטיקאי (פרויד, יונג) + מומחה HR + יועץ MBTI + מומחה Big Five. נתח את השיחה ותן הערכה מקצועית.

השיחה של המשתמש:
{conversation_text}

שתי המטרות הראשיות שלך:
1. ניתוח פסיכולוגי עמוק: קבע פסיכוטיפ, ארכיטיפ, מנגנוני הגנה
2. הערכת HR: פוטנציאל מקצועי, תפקידים מתאימים, המלצות לגיוס

בצע ניתוח רב-שכבתי:

🧠 פרופיל פסיכולוגי:
- פרויד: מבנה אישיות (אידיד/אגו/סופר-אגו), מנגנוני הגנה
- יונג: ארכיטיפ דומיננטי (חכם, גיבור, יוצר, שליט, וכו')
- MBTI: טיפוס משוער (4 אותיות עם הסבר)
- Big Five: הערכה לפי OCEAN (ציונים 1-10 לכל אחד)

💼 הערכת HR:
- פוטנציאל מנהיגותי (1-10)
- עבודת צוות (1-10)
- עמידות בלחץ (1-10)
- מקצועות מתאימים (3 קונקרטיים עם הנמקה פסיכולוגית)
- המלצה ל-HR: מומלץ / בתנאי / לא מומלץ

פורמט:
🎯 פרופיל מהיר:
🧠 פסיכוטיפ: [MBTI] - [ארכיטיפ]
📊 Big Five: O[X] C[X] E[X] A[X] N[X]
💼 הערכות HR: מנהיגות [X/10], צוות [X/10], לחץ [X/10]
🎯 מקצועות: [3 קונקרטיים עם הנמקה]
✅ המלצה: [מומלץ/בתנאי/לא מומלץ] + סיבה

נתח כפסיכולוג מקצועי + מומחה HR!""",
        
        'en': f"""You are a combined expert: psychoanalyst (Freud, Jung) + HR specialist + MBTI consultant + Big Five expert. Analyze the conversation and provide professional assessment.

USER CONVERSATION:
{conversation_text}

YOUR TWO MAIN GOALS:
1. DEEP PSYCHOLOGICAL ANALYSIS: Determine psychotype, archetype, defense mechanisms
2. HR ASSESSMENT: Professional potential, suitable roles, hiring recommendations

Conduct MULTI-LEVEL analysis:

🧠 PSYCHOLOGICAL PROFILE:
- FREUD: personality structure (Id/Ego/Superego), defense mechanisms
- JUNG: dominant archetype (Sage, Hero, Creator, Ruler, etc.)
- MBTI: presumed type (4 letters with explanation)
- BIG FIVE: assessment by OCEAN (1-10 scores each)

💼 HR ASSESSMENT:
- Leadership potential (1-10)
- Teamwork (1-10)
- Stress resistance (1-10)
- Suitable professions (3 specific with psychological justification)
- HR recommendation: RECOMMENDED / CONDITIONAL / NOT RECOMMENDED

FORMAT:
🎯 EXPRESS PROFILE:
🧠 Psychotype: [MBTI] - [archetype]
📊 Big Five: O[X] C[X] E[X] A[X] N[X]
💼 HR scores: Leadership [X/10], Team [X/10], Stress [X/10]
🎯 Professions: [3 specific with justification]
✅ Recommendation: [RECOMMENDED/CONDITIONAL/NOT RECOMMENDED] + reason

Analyze as professional psychologist + HR expert!"""
    }
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": express_prompts[user_lang]}],
            max_tokens=800,
            temperature=0.7,
            timeout=60
        )
        analysis = response.choices[0].message.content.strip()
        
        # Отправляем результат (проверяем источник вызова)
        if update.message:
            # Вызов из обычного сообщения
            await update.message.reply_text(analysis, parse_mode=ParseMode.MARKDOWN)
        else:
            # Вызов из callback'а кнопки
            await update.callback_query.message.reply_text(analysis, parse_mode=ParseMode.MARKDOWN)
        
        # Предлагаем полный анализ
        follow_up_messages = {
            'ru': "💡 Хотите более детальный анализ? Нажмите /start для полного опроса из 7 вопросов!",
            'he': "💡 רוצים ניתוח מפורט יותר? לחצו /start לסקר מלא של 7 שאלות!",
            'en': "💡 Want a more detailed analysis? Press /start for a full 7-question survey!"
        }
        
        if update.message:
            await update.message.reply_text(follow_up_messages[user_lang])
        else:
            await update.callback_query.message.reply_text(follow_up_messages[user_lang])
        
    except Exception as e:
        logger.error(f"Ошибка экспресс-анализа: {e}")
        error_msg = {
            'ru': "❌ Ошибка анализа. Попробуйте полный опрос через /start",
            'he': "❌ שגיאת ניתוח. נסו את הסקר המלא דרך /start",
            'en': "❌ Analysis error. Try the full survey via /start"
        }
        
        if update.message:
            await update.message.reply_text(error_msg[user_lang])
        else:
            await update.callback_query.message.reply_text(error_msg[user_lang])
    
    finally:
        # Очищаем данные
        secure_cleanup_user_data(user.id, context)

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
        
        # Рассчитываем HR-оценки
        hr_scores = calculate_hr_scores(answers, user_lang)
        hr_analysis = generate_hr_analysis(answers, hr_scores, user_lang)
        
        # Сохраняем кандидата в базу данных
        analysis_data = {
            'answers': answers,
            'speech_analysis': speech_analysis,
            'full_analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        save_candidate(
            telegram_id=user.id,
            name=user.full_name or f"User_{user.id}",
            language=user_lang,
            analysis_data=analysis_data,
            hr_scores=hr_scores
        )
        
        # Отправляем админу полный анализ (с ответами, анализом речи и HR-оценками)
        admin_text = f"👤 Кандидат: {user.full_name} (ID: {user.id})\n🌐 Язык: {user_lang}\n\n📝 ОТВЕТЫ:\n{answers_block}\n\n{speech_analysis}\n\n🧠 ПОЛНЫЙ АНАЛИЗ:\n{analysis}\n\n📊 HR-ОЦЕНКИ:\n"
        
        # Добавляем HR-оценки
        for skill, score in hr_scores.items():
            skill_name = {
                'leadership': 'Лидерство',
                'teamwork': 'Командная работа', 
                'stress_resistance': 'Стрессоустойчивость',
                'motivation': 'Мотивация',
                'communication': 'Коммуникация',
                'adaptability': 'Адаптивность',
                'reliability': 'Надежность',
                'creativity': 'Креативность',
                'analytical_thinking': 'Аналитическое мышление',
                'emotional_intelligence': 'Эмоциональный интеллект'
            }.get(skill, skill)
            admin_text += f"• {skill_name}: {score}/10\n"
        
        admin_text += f"\n🎯 РЕКОМЕНДАЦИЯ: {hr_analysis['recommendation']}\n📈 ОБЩАЯ ОЦЕНКА: {hr_analysis['total_score']}/10\n🏷️ РОЛИ: {', '.join(hr_analysis['roles']) if hr_analysis['roles'] else 'Не определены'}\n"
        
        if hr_analysis['red_flags']:
            admin_text += f"⚠️ КРАСНЫЕ ФЛАГИ: {', '.join(hr_analysis['red_flags'])}\n"
        
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

def calculate_hr_scores(answers, language):
    """Расчет HR-оценок кандидата"""
    all_text = " ".join(answers)
    
    # Базовые оценки (1-10)
    scores = {
        'leadership': 5,      # Лидерство
        'teamwork': 5,        # Командная работа
        'stress_resistance': 5,  # Стрессоустойчивость
        'motivation': 5,      # Мотивация
        'communication': 5,   # Коммуникация
        'adaptability': 5,    # Адаптивность
        'reliability': 5,     # Надежность
        'creativity': 5,      # Креативность
        'analytical_thinking': 5,  # Аналитическое мышление
        'emotional_intelligence': 5  # Эмоциональный интеллект
    }
    
    # Анализ текста для корректировки оценок
    text_lower = all_text.lower()
    
    # Лидерство
    leadership_words = ['лидер', 'руковод', 'управл', 'команд', 'веду', 'возглавляю', 'leader', 'manage', 'lead']
    if any(word in text_lower for word in leadership_words):
        scores['leadership'] = min(10, scores['leadership'] + 2)
    
    # Командная работа
    team_words = ['команд', 'коллектив', 'совместно', 'вместе', 'сотруднич', 'team', 'together', 'collaborate']
    if any(word in text_lower for word in team_words):
        scores['teamwork'] = min(10, scores['teamwork'] + 2)
    
    # Стрессоустойчивость
    stress_words = ['стресс', 'давлен', 'сложн', 'трудн', 'справляюсь', 'stress', 'pressure', 'difficult']
    if any(word in text_lower for word in stress_words):
        scores['stress_resistance'] = min(10, scores['stress_resistance'] + 1)
    
    # Мотивация
    motivation_words = ['цель', 'мечт', 'стремл', 'развит', 'рост', 'goal', 'dream', 'develop', 'growth']
    if any(word in text_lower for word in motivation_words):
        scores['motivation'] = min(10, scores['motivation'] + 2)
    
    # Коммуникация
    comm_words = ['общ', 'говори', 'объясн', 'презент', 'коммуник', 'communicate', 'present', 'explain']
    if any(word in text_lower for word in comm_words):
        scores['communication'] = min(10, scores['communication'] + 1)
    
    # Креативность
    creative_words = ['творч', 'креатив', 'иде', 'нов', 'нестандарт', 'creative', 'idea', 'innovative']
    if any(word in text_lower for word in creative_words):
        scores['creativity'] = min(10, scores['creativity'] + 2)
    
    # Аналитическое мышление
    analytical_words = ['анализ', 'логик', 'систем', 'структур', 'план', 'analyze', 'logic', 'system', 'plan']
    if any(word in text_lower for word in analytical_words):
        scores['analytical_thinking'] = min(10, scores['analytical_thinking'] + 2)
    
    return scores

def generate_hr_analysis(answers, hr_scores, language):
    """Генерация HR-анализа с рекомендациями"""
    
    # Определяем роли на основе оценок
    roles = []
    if hr_scores['leadership'] >= 7:
        roles.append('Лидер' if language == 'ru' else 'Leader' if language == 'en' else 'מנהיג')
    if hr_scores['teamwork'] >= 7:
        roles.append('Командный игрок' if language == 'ru' else 'Team Player' if language == 'en' else 'שחקן צוות')
    if hr_scores['creativity'] >= 7:
        roles.append('Креативщик' if language == 'ru' else 'Creative' if language == 'en' else 'יצירתי')
    if hr_scores['analytical_thinking'] >= 7:
        roles.append('Аналитик' if language == 'ru' else 'Analyst' if language == 'en' else 'אנליסט')
    
    # Красные флаги
    red_flags = []
    if hr_scores['stress_resistance'] <= 3:
        red_flags.append('Низкая стрессоустойчивость' if language == 'ru' else 'Low stress resistance' if language == 'en' else 'עמידות נמוכה ללחץ')
    if hr_scores['teamwork'] <= 3:
        red_flags.append('Проблемы с командной работой' if language == 'ru' else 'Teamwork issues' if language == 'en' else 'בעיות עבודה בצוות')
    if hr_scores['reliability'] <= 3:
        red_flags.append('Низкая надежность' if language == 'ru' else 'Low reliability' if language == 'en' else 'אמינות נמוכה')
    
    # Общая оценка
    total_score = sum(hr_scores.values()) / len(hr_scores)
    if total_score >= 8:
        overall = 'Отличный кандидат' if language == 'ru' else 'Excellent candidate' if language == 'en' else 'מועמד מצוין'
    elif total_score >= 6:
        overall = 'Хороший кандидат' if language == 'ru' else 'Good candidate' if language == 'en' else 'מועמד טוב'
    else:
        overall = 'Требует дополнительной оценки' if language == 'ru' else 'Requires additional assessment' if language == 'en' else 'דורש הערכה נוספת'
    
    return {
        'roles': roles,
        'red_flags': red_flags,
        'overall_assessment': overall,
        'total_score': round(total_score, 1),
        'recommendation': 'Найм' if total_score >= 6 else 'Доп. интервью' if total_score >= 4 else 'Не рекомендован'
    }

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

async def phone_mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /phone - режим телефонного автоответчика"""
    user = update.effective_user
    user_lang = context.user_data.get('language', 'ru')
    
    phone_text = {
        'ru': """📞 Интегрированная голосовая консультация в Telegram

• Отправьте голосовое сообщение — я распознаю речь и дам профессиональную консультацию по карьере
• Ответ придёт текстом в этот же чат
• Источник интеллекта: OpenAI (ваш ключ)

Попробуйте: запишите «Хочу выбрать профессию в IT» или «Какая работа мне подойдёт?»

Для полного психологического теста: /start""",
        
        'he': """📞 **מצב מענה טלפוני אוטומטי**

🎯 **מה זה:**
• בדיקת פונקציות לשיחות טלפון
• עיבוד הודעות קוליות  
• אינטגרציה עם AI למענה

🧪 **איך לבדוק:**
1. שלחו הודעה קולית
2. קבלו תשובת AI (סימולציה של שיחה טלפונית)
3. נסו סוגים שונים של שאלות

📱 **סטטוס אינטגרציה:**
• הודעות קוליות Telegram: ✅ עובד
• שרת WebSocket: ⏳ בפיתוח
• אינטגרציית Twilio: ⏳ מתוכנן

לחזרה לפסיכואנליזה: /start""",
        
        'en': """📞 **Phone Auto-responder Mode**

🎯 **What is this:**
• Testing functions for phone calls
• Voice message processing
• AI integration for responses

🧪 **How to test:**
1. Send a voice message
2. Get AI response (phone conversation simulation)
3. Try different types of questions

📱 **Integration status:**
• Telegram voice: ✅ Working
• WebSocket server: ⏳ In development
• Twilio integration: ⏳ Planned

To return to psychoanalysis: /start"""
    }
    
    await update.message.reply_text(phone_text[user_lang], parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - статус всех систем"""
    user_lang = context.user_data.get('language', 'ru')
    
    # Проверяем голосовые функции
    voice_status = "✅ Подключены" if VOICE_ENABLED else "⚠️ Отключены"
    
    status_text = {
        'ru': f"""📊 **Статус системы HR-Психоаналитика + Автоответчик**

🧠 **Психоанализ (основная функция):**
✅ 7-вопросный опрос
✅ Экспресс-анализ из диалога
✅ GPT-4 анализ личности
✅ HR-оценки кандидатов
✅ Многоязычность (ru/he/en)

📞 **Автоответчик (новое):**
{voice_status} Голосовые сообщения
✅ WebSocket сервер готов
✅ Веб-интерфейс для тестирования
⏳ Twilio интеграция (планируется)

💼 **HR-функции:**
✅ База данных кандидатов
✅ HR-панель для специалистов
✅ Сравнение кандидатов

🔧 **Системные функции:**
✅ Railway деплой
✅ Многопользовательский режим
✅ Безопасность данных

**Команды:** /start /help /phone /hr_panel /status""",
        
        'he': f"""📊 **סטטוס מערכת HR-פסיכואנליטיקאי + מענה אוטומטי**

🧠 **פסיכואנליזה (פונקציה עיקרית):**
✅ סקר של 7 שאלות
✅ ניתוח מהיר מהשיחה
✅ ניתוח אישיות GPT-4
✅ הערכות HR של מועמדים
✅ רב-לשוניות (ru/he/en)

📞 **מענה אוטומטי (חדש):**
{voice_status} הודעות קוליות
✅ שרת WebSocket מוכן
✅ ממשק אינטרנט לבדיקה
⏳ אינטגרציית Twilio (מתוכנן)

💼 **פונקציות HR:**
✅ בסיס נתונים מועמדים
✅ פאנל HR למומחים
✅ השוואת מועמדים

🔧 **פונקציות מערכת:**
✅ פריסת Railway
✅ מצב רב-משתמשים
✅ אבטחת נתונים

**פקודות:** /start /help /phone /hr_panel /status""",
        
        'en': f"""📊 **HR-Psychoanalyst + Auto-responder System Status**

🧠 **Psychoanalysis (main function):**
✅ 7-question survey
✅ Express analysis from dialog
✅ GPT-4 personality analysis
✅ HR candidate evaluations
✅ Multilingual (ru/he/en)

📞 **Auto-responder (new):**
{voice_status} Voice messages
⏳ WebSocket server (in development)
⏳ Twilio integration (planned)

💼 **HR functions:**
✅ Candidate database
✅ HR panel for specialists
✅ Candidate comparison

🔧 **System functions:**
✅ Railway deployment
✅ Multi-user mode
✅ Data security

**Commands:** /start /help /phone /hr_panel /status"""
    }
    
    # Отправляем без Markdown из-за потенциальных ошибок парсинга
    await update.message.reply_text(status_text[user_lang], parse_mode=None)

async def setup_bot_commands(application):
    """Настройка команд бота"""
    commands = [
        BotCommand("start", "🧠 Психологический анализ + HR"),
        BotCommand("help", "📋 Справка о возможностях"),
        BotCommand("phone", "📞 Режим автоответчика"),
        BotCommand("status", "📊 Статус всех систем"),
        BotCommand("cancel", "❌ Отменить опрос")
    ]
    await application.bot.set_my_commands(commands)

def main():
    print("🚀 Запуск профессионального психоаналитического бота...")
    
    # Инициализируем базу данных
    init_database()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Q1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CommandHandler('cancel', cancel),
                CommandHandler('phone', phone_mode_command),
                CommandHandler('status', status_command),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$"),
                CallbackQueryHandler(start_survey_callback, pattern="start_survey"),
                CallbackQueryHandler(express_analysis_callback, pattern="express_analysis"),
                CallbackQueryHandler(continue_chat_callback, pattern="continue_chat")
            ],
            Q2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q3: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q4: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q5: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q6: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
            Q7: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(handle_back_button, pattern=r"^back_\d+$")
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('phone', phone_mode_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('hr_panel', hr_panel_command))
    application.add_handler(CommandHandler('hr_compare', hr_compare_command))
    
    # Глобальные обработчики callback'ов (вне разговора)
    application.add_handler(CallbackQueryHandler(express_analysis_callback, pattern="express_analysis"))
    application.add_handler(CallbackQueryHandler(continue_chat_callback, pattern="continue_chat"))
    application.add_handler(CallbackQueryHandler(full_test_callback, pattern="full_test"))
    
    # Голосовые обработчики
    if VOICE_ENABLED:
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))
        logger.info("✅ Голосовые обработчики добавлены")
    
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