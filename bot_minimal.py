import os
import re
import logging
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

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения")


# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


# RU-only texts and questions
QUESTIONS_RU = [
    "Опишите себя в нескольких словах. Какие качества считаете главными в своём характере?",
    "Что вам даёт энергию в течение дня? Откуда черпаете силы и мотивацию?",
    "Что раздражает больше: хаос или рутина? Почему?",
    "Когда перед вами выбор — что делаете в первую очередь? Как принимаете решения?",
    "Вы чаще думаете о прошлом, настоящем или будущем? Пример, пожалуйста.",
    "Что предпочитаете: говорить или писать? Когда и почему?",
    "Как относитесь к контролю — любите управлять или предпочитаете свободу? Объясните.",
]


HELP_TEXT_RU = (
    "🤖 Возможности:\n"
    "• Экспресс-анализ сообщений\n"
    "• Полный опрос из 7 вопросов (Фрейд, Юнг, MBTI, Big Five, HR)\n\n"
    "Как пользоваться:\n"
    "1) Выберите формат — экспресс или полный опрос.\n"
    "2) Отвечайте развёрнуто — так анализ точнее.\n"
    "3) Можно просто общаться — бот задаёт умные вопросы.\n\n"
    "Важно: это не медицинская помощь. Ответы — краткие и поддерживающие."
)

GREET_RU = (
    "🎯 Карьерный психоаналитик\n\n"
    "Определю ваш психотип и подходящие роли. Выберите формат:\n"
)


# States for ConversationHandler
(Q1, Q2, Q3, Q4, Q5, Q6, Q7) = range(7)


# In-memory storage
user_answers = {}
conversation_history = {}


def get_navigation_keyboard(current_index: int) -> InlineKeyboardMarkup | None:
    if current_index > 0:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton('⬅️ Назад', callback_data=f"back_{current_index-1}")]]
        )
    return None


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ Экспресс-анализ", callback_data='express_analysis')],
            [InlineKeyboardButton("📋 Полный тест", callback_data='full_test')],
            [InlineKeyboardButton("📘 Справка", callback_data='help_show')],
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
        await update.message.reply_text(resp.choices[0].message.content.strip(), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Ошибка экспресс-анализа: {e}")
        await update.message.reply_text("❌ Ошибка экспресс-анализа. Попробуйте полный опрос.")


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"{GREET_RU}\n"
        "• ⚡ Экспресс-анализ — быстро по диалогу\n"
        "• 📋 Полный тест — 7 вопросов с глубоким профилем\n"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN)


# COMMANDS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_answers.pop(user.id, None)
    conversation_history.pop(user.id, None)
    await show_main_menu(update, context)
    return Q1


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT_RU)


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
    await q.edit_message_text(
        f"📋 Начинаем опрос (1/7)\n\n{QUESTIONS_RU[0]}",
        reply_markup=get_navigation_keyboard(0),
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
        if msg_count in (3, 5):
            keyboard = [
                [InlineKeyboardButton("⚡ Экспресс-анализ", callback_data='express_analysis')],
                [InlineKeyboardButton("📋 Полный тест", callback_data='full_test')],
                [InlineKeyboardButton("💬 Еще поговорить", callback_data='continue_chat')],
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
            errors.get(err, errors['too_short']), reply_markup=get_navigation_keyboard(state)
        )
        return state

    answers = user_answers.setdefault(user.id, [None] * 7)
    answers[state] = text

    if state < 6:
        next_state = state + 1
        context.user_data['state'] = next_state
        await update.message.reply_text(
            f"{next_state+1}/7. {QUESTIONS_RU[next_state]}",
            reply_markup=get_navigation_keyboard(next_state),
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
    answers_block = "\n".join(
        f"{i+1}) {q}\nОтвет: {a}\n" for i, (q, a) in enumerate(zip(QUESTIONS_RU, answers))
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
            [InlineKeyboardButton("⚡ Экспресс-анализ", callback_data='express_analysis')],
            [InlineKeyboardButton("📋 Полный тест", callback_data='full_test')],
            [InlineKeyboardButton("💬 Еще поговорить", callback_data='continue_chat')],
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
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))

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

    # Out of conversation generic messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message))

    logger.info("Бот запущен (расширенный RU)")
    application.run_polling(allowed_updates=['message', 'callback_query'])


if __name__ == "__main__":
    main()
