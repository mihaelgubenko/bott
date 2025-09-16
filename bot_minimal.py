import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import openai

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT_RU = (
    "Ты — профессиональный психолог-психоаналитик и карьерный консультант. "
    "Отвечай ТОЛЬКО на русском языке. Используй мягкий, эмпатичный стиль. "
    "Основывайся на подходах Фрейда, Юнга, MBTI и Big Five, но объясняй просто. "
    "Делай краткий экспресс-анализ: 1) наблюдения о личности; 2) мотивы; 3) рекомендации; 4) при уместности — направления карьеры. "
    "Избегай медицинских диагнозов, давай поддерживающие, практичные советы."
)


def build_openai_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=OPENAI_API_KEY)


async def ai_reply(user_text: str, user_name: str) -> str:
    try:
        client = build_openai_client()
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RU},
                {"role": "user", "content": f"Имя пользователя: {user_name}. Сообщение: {user_text}"},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка OpenAI: {e}")
        return (
            "Сейчас не могу подключиться к аналитике. Попробуйте позже. "
            "Опишите кратко, что вас беспокоит и какой результат хотите — помогу сформулировать шаги."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🎯 Психоанализ и экспресс‑консультация\n\n"
        "Напишите, что вас волнует: мысли, переживания, цели, конфликты, сны.\n"
        "Я дам мягкий, практичный разбор и рекомендации.\n\n"
        "Команды:\n/ help — подсказка\n/ cancel — сброс состояния"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Как пользоваться:\n"
        "1) Напишите сообщение о ситуации или вопросе.\n"
        "2) Получите краткий анализ личности и рекомендации.\n"
        "3) Можно продолжать диалог — учитываю контекст.\n\n"
        "Важно: это не медицинская помощь. Отвечаю только на русском."
    )
    await update.message.reply_text(text)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Состояние сброшено. Можете задать новый вопрос.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_text = update.message.text or ""
    if not user_text.strip():
        await update.message.reply_text("Опишите, пожалуйста, вашу ситуацию или вопрос.")
        return
    reply = await ai_reply(user_text, user.first_name or "Пользователь")
    await update.message.reply_text(reply)


def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Бот запущен (минимальный режим RU)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
