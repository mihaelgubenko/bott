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

# Новые модули для ИИ-улучшений
from sentiment_analyzer import get_sentiment_analyzer
from prompt_ab_testing import get_ab_testing_manager, PromptType
from machine_learning_system import get_ml_system, UserProfile, UserStyle
from feedback_system import get_feedback_system, FeedbackType
from adaptive_prompts import get_adaptive_prompt_system, PromptType as AdaptivePromptType, UserContext
from learning_analytics import get_learning_analytics

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

# ИИ модули
sentiment_analyzer = get_sentiment_analyzer()
ab_testing_manager = get_ab_testing_manager()
ml_system = get_ml_system()
feedback_system = get_feedback_system()
adaptive_prompt_system = get_adaptive_prompt_system()
learning_analytics = get_learning_analytics()

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

# Speech pattern analysis
def analyze_speech_patterns(text: str) -> dict:
    """Анализ паттернов речи для определения роли ИИ"""
    text_lower = text.lower()
    
    patterns = {
        'psychology_need': False,
        'career_need': False,
        'emotional_support': False,
        'cancellation': False,
        'provocative': False,
        'topic_change': False,
        'self_introduction_request': False,
        'dream_expression': False
    }
    
    # Психологическая помощь
    psychology_keywords = ['сон', 'сны', 'депрессия', 'тревога', 'стресс', 'паника', 'страх', 'грусть', 'одиночество', 'отношения', 'семья', 'родители', 'дети', 'любовь', 'развод', 'смерть', 'потеря', 'плохо', 'больно', 'страшно']
    if any(keyword in text_lower for keyword in psychology_keywords):
        patterns['psychology_need'] = True
    
    # Карьерные вопросы
    career_keywords = ['работа', 'карьера', 'профессия', 'зарплата', 'деньги', 'учеба', 'образование', 'навыки', 'опыт', 'компания', 'начальник', 'коллеги']
    if any(keyword in text_lower for keyword in career_keywords):
        patterns['career_need'] = True
    
    # Эмоциональная поддержка
    emotional_keywords = ['одинок', 'грустно', 'плохо', 'устал', 'устала', 'сложно', 'трудно', 'помоги', 'поддержка', 'понимаю', 'понимаешь']
    if any(keyword in text_lower for keyword in emotional_keywords):
        patterns['emotional_support'] = True
    
    # Отмена/прекращение
    cancellation_keywords = ['не хочу', 'хватит', 'достаточно', 'стоп', 'прекрати', 'остановись', 'не буду', 'не буду говорить', 'не хочу говорить', 'хватит говорить']
    if any(keyword in text_lower for keyword in cancellation_keywords):
        patterns['cancellation'] = True
    
    # Смена темы
    topic_change_keywords = ['другое', 'другая тема', 'давай о', 'поговорим о', 'хочу поговорить о', 'смени тему', 'не об этом']
    if any(keyword in text_lower for keyword in topic_change_keywords):
        patterns['topic_change'] = True
    
    # Запрос рассказать о себе
    self_intro_keywords = ['расскажи о себе', 'расскажи о тебе', 'кто ты', 'что ты', 'как ты работаешь', 'твоя история', 'твоя работа', 'что ты умеешь', 'что умеешь']
    if any(keyword in text_lower for keyword in self_intro_keywords):
        patterns['self_introduction_request'] = True
    
    # Мечты и цели
    dream_keywords = ['хочу стать', 'мечтаю', 'мечта', 'цель', 'планирую', 'буду', 'стану']
    if any(keyword in text_lower for keyword in dream_keywords):
        patterns['dream_expression'] = True
    
    # Провокационные вопросы и непонимание
    provocative_keywords = ['глупый', 'тупой', 'бесполезный', 'не понимаешь', 'не слушаешь', 'плохой', 'ужасный', 'ненавижу', 'ненавидишь', 'не понял', 'не поняла', 'не понимаешь меня']
    if any(keyword in text_lower for keyword in provocative_keywords):
        patterns['provocative'] = True
    
    return patterns

# Professional prompts with A/B testing
def get_express_analysis_prompt(conversation: str, message_count: int, user_id: int) -> Tuple[str, str]:
    """Получить промпт для экспресс-анализа с учетом A/B тестирования"""
    template, variant_id = ab_testing_manager.get_prompt_for_user(user_id, PromptType.EXPRESS_ANALYSIS)
    
    if not template:
        # Fallback к стандартному промпту
        template = """
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
        variant_id = "default"
    
    prompt = template.format(conversation=conversation, message_count=message_count)
    return prompt, variant_id

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

def get_psychology_consultation_prompt(user_message: str, user_id: int, conversation_history: list = None) -> Tuple[str, str]:
    """Получить промпт для психологической консультации с учетом A/B тестирования и анализа настроения"""
    # Анализ настроения пользователя
    sentiment_result = sentiment_analyzer.analyze_text(user_message)
    
    # Получаем базовый промпт через A/B тестирование
    template, variant_id = ab_testing_manager.get_prompt_for_user(user_id, PromptType.PSYCHOLOGY_CONSULTATION)
    
    if not template:
        # Fallback к стандартному промпту с контекстом
        template = """
Ты — опытный психолог с большим сердцем. Твоя главная задача - ПОДДЕРЖАТЬ и ПОНИМАТЬ.

ИСТОРИЯ РАЗГОВОРА:
{conversation_context}

ТЕКУЩЕЕ СООБЩЕНИЕ КЛИЕНТА:
{user_message}

ВАЖНО: Если клиент ссылается на предыдущие части разговора ("мы говорили об этом", "выше", "раньше"), обязательно учитывай контекст из истории разговора.

ТВОЯ РОЛЬ: Друг-психолог, который всегда на стороне человека и ПОМНИТ весь разговор.

ПРИНЦИПЫ:
- СНАЧАЛА прояви эмпатию и понимание
- УЧИТЫВАЙ всю историю разговора
- НЕ давай советы, если человек не просит
- Поддерживай эмоционально
- Будь теплым и человечным
- Если человек говорит "не понял" или ссылается на предыдущее - обратись к контексту

ФОРМАТ ОТВЕТА:
💙 Эмпатичный ответ (понимание чувств с учетом контекста)
🤗 Поддержка и принятие
💡 Мягкие рекомендации (если уместно)

СТИЛЬ: Теплый, понимающий, как разговор с близким другом, который помнит всё. 150-300 слов.
"""
        variant_id = "default"
    
    # Подготавливаем контекст разговора
    conversation_context = ""
    if conversation_history and len(conversation_history) > 1:
        # Берем последние 10 сообщений для контекста
        recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history[:-1]  # исключаем текущее сообщение
        conversation_context = "Предыдущие сообщения:\n" + "\n".join([f"- {msg}" for msg in recent_messages])
    else:
        conversation_context = "Это первое сообщение в разговоре."
    
    # Получаем профиль пользователя для адаптации
    user_profile = ml_system.get_user_profile(user_id)
    
    # Создаем контекст пользователя для адаптивных промптов
    if user_profile:
        user_context = UserContext(
            user_id=user_id,
            preferred_style=UserStyle(user_profile.preferred_style),
            psychological_traits=user_profile.psychological_traits,
            communication_patterns=user_profile.communication_patterns,
            interests=user_profile.interests,
            session_context={
                'session_length': len(conversation_history) if conversation_history else 0,
                'request_type': 'psychology_consultation'
            },
            conversation_history=conversation_history or []
        )
        
        # Генерируем адаптивный промпт
        adaptive_prompt = adaptive_prompt_system.generate_adaptive_prompt(
            user_context=user_context,
            prompt_type=AdaptivePromptType.PSYCHOLOGY_CONSULTATION,
            additional_context={
                'sentiment': sentiment_result.overall_sentiment,
                'interests': user_profile.interests
            }
        )
        
        # Используем адаптивный промпт
        template = adaptive_prompt.final_prompt
        
        # Записываем использование адаптивного промпта
        adaptive_prompt_system.record_prompt_usage(
            user_id=user_id,
            prompt_type=AdaptivePromptType.PSYCHOLOGY_CONSULTATION,
            user_style=user_context.preferred_style,
            adaptations_count=len(adaptive_prompt.adaptations)
        )
    
    # Форматируем промпт с учетом анализа настроения
    sentiment_info = f"""Настроение: {sentiment_result.overall_sentiment} (уверенность: {sentiment_result.confidence:.2f})
Рекомендуемый стиль ответа: {sentiment_result.recommendation}
Психологические показатели: стресс={sentiment_result.psychological_indicators.get('stress_level', 0):.2f}, тревога={sentiment_result.psychological_indicators.get('anxiety_level', 0):.2f}"""
    
    if '{sentiment_analysis}' in template:
        prompt = template.format(
            user_message=user_message, 
            conversation_context=conversation_context,
            sentiment_analysis=sentiment_info
        )
    elif '{conversation_context}' in template:
        prompt = template.format(
            user_message=user_message,
            conversation_context=conversation_context
        )
    else:
        prompt = template.format(user_message=user_message)
    
    return prompt, variant_id

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
🤗 **HR-Психоаналитик | Карьерный консультант**

Привет! Я ваш персональный помощник, специализирующийся на:

💙 **Психологической поддержке** - выслушаю и поддержу
🧠 **Анализе личности** - помогу понять себя и свои чувства  
🤝 **Психологической консультации** - сны, стресс, отношения
💼 **Карьерном консультировании** - выбор профессии и развития

**Как я работаю:**
• Просто общайтесь со мной естественно
• После 10 сообщений проведу экспресс-анализ (бесплатно)
• Для детального психоанализа скажите 'полный анализ'
• Использую ИИ для анализа эмоций и настроения
• Постоянно улучшаюсь через A/B тестирование

**Конфиденциально и анонимно** 💙
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
/reset - сбросить бота
/stats - статистика (только админ)
/dashboard - дашборд самообучения (только админ)
/feedback - статистика обратной связи (только админ)
/insights - инсайты для улучшения (только админ)

**🤖 ИИ-возможности:**
• Анализ эмоций и настроения в реальном времени
• A/B тестирование промптов для лучших ответов
• Персонализация на основе стиля общения

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
        cursor.execute('DELETE FROM user_variant_assignments')  # Очищаем A/B назначения
        cursor.execute('DELETE FROM ab_test_results')  # Очищаем результаты тестов
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            "✅ Память бота полностью очищена:\n"
            "• Очищена RAM память\n"
            "• Очищена база данных\n"
            "• Все диалоги удалены\n"
            "• A/B тесты сброшены\n\n"
            "💡 Для очистки кэша Telegram перезапустите бота командой /start"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при очистке: {e}")

async def reset_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сбросить бота (очистить кэш Telegram)"""
    user = update.effective_user
    
    # Очистка данных пользователя
    user_data.pop(user.id, None)
    conversation_history.pop(user.id, None)
    
    await update.message.reply_text(
        "🔄 Бот сброшен!\n\n"
        "Все ваши данные очищены. Начните заново с /start"
    )

async def show_ab_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статистику A/B тестирования (только для админов)"""
    user = update.effective_user
    
    # Проверка на админа (можно настроить)
    if user.id != 123456789:  # Замените на ваш Telegram ID
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        stats = ab_testing_manager.get_test_statistics()
        
        if not stats:
            await update.message.reply_text("📊 Пока нет данных для A/B тестирования")
            return
        
        message = "📊 **Статистика A/B тестирования:**\n\n"
        
        for variant_id, data in stats.items():
            message += f"**{data['name']}** (`{variant_id}`)\n"
            message += f"• Использований: {data['total_uses']}\n"
            message += f"• Конверсия: {data['conversion_rate']:.1%}\n"
            message += f"• Качество: {data['avg_quality']:.2f}/1.0\n"
            message += f"• Оценка пользователей: {data['avg_feedback']:.1f}/5.0\n\n"
        
        # Определяем лучшие варианты
        express_winner = ab_testing_manager.get_winning_variant(PromptType.EXPRESS_ANALYSIS)
        psych_winner = ab_testing_manager.get_winning_variant(PromptType.PSYCHOLOGY_CONSULTATION)
        
        message += "🏆 **Лучшие варианты:**\n"
        if express_winner:
            message += f"• Экспресс-анализ: `{express_winner}`\n"
        if psych_winner:
            message += f"• Психологическая консультация: `{psych_winner}`\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error showing AB stats: {e}")
        await update.message.reply_text(f"❌ Ошибка при получении статистики: {e}")

async def show_learning_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать дашборд обучения ИИ (только для админов)"""
    user = update.effective_user
    
    # Проверка на админа
    if user.id != 123456789:  # Замените на ваш Telegram ID
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        # Получаем данные дашборда
        dashboard_data = learning_analytics.get_learning_dashboard_data()
        
        # Формируем сообщение
        message = "🧠 **Дашборд самообучения ИИ:**\n\n"
        
        # Текущие метрики
        metrics = dashboard_data['current_metrics']
        message += "📈 **Текущие метрики:**\n"
        message += f"• Удовлетворенность: {metrics['user_satisfaction']:.2f}/1.0\n"
        message += f"• Качество ответов: {metrics['response_quality']:.2f}/1.0\n"
        message += f"• Вовлеченность: {metrics['engagement_score']:.2f}/1.0\n"
        message += f"• Конверсия: {metrics['conversion_rate']:.1%}\n"
        message += f"• Активные пользователи: {metrics['active_users']}\n\n"
        
        # Тренды
        message += "📊 **Тренды (7 дней):**\n"
        for trend in dashboard_data['trends']:
            direction_emoji = "📈" if trend['trend_direction'] == 'up' else "📉" if trend['trend_direction'] == 'down' else "➡️"
            message += f"• {trend['metric_name']}: {direction_emoji} (сила: {trend['trend_strength']:.2f})\n"
        
        # Инсайты
        insights = dashboard_data['insights_summary']
        message += f"\n💡 **Активные инсайты:**\n"
        message += f"• Ожидают: {insights['pending_insights']}\n"
        message += f"• В реализации: {insights['implementing_insights']}\n"
        
        # Общий индекс здоровья
        health_score = dashboard_data['overall_health_score']
        health_emoji = "🟢" if health_score > 0.7 else "🟡" if health_score > 0.5 else "🔴"
        message += f"\n{health_emoji} **Индекс здоровья системы:** {health_score:.2f}/1.0\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error showing learning dashboard: {e}")
        await update.message.reply_text(f"❌ Ошибка при получении дашборда: {e}")

async def show_feedback_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статистику обратной связи (только для админов)"""
    user = update.effective_user
    
    # Проверка на админа
    if user.id != 123456789:  # Замените на ваш Telegram ID
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        # Получаем статистику обратной связи
        feedback_stats = feedback_system.get_feedback_statistics(days=7)
        
        # Формируем сообщение
        message = "📝 **Статистика обратной связи (7 дней):**\n\n"
        message += f"• Всего отзывов: {feedback_stats['total_feedback']}\n"
        
        if feedback_stats['average_rating']:
            message += f"• Средняя оценка: {feedback_stats['average_rating']:.1f}/5.0\n"
        
        message += f"• 👍 Лайков: {feedback_stats['thumbs_up']}\n"
        message += f"• 👎 Дизлайков: {feedback_stats['thumbs_down']}\n"
        message += f"• Активных инсайтов: {feedback_stats['pending_insights']}\n\n"
        
        # Статистика по типам
        message += "📊 **По типам обратной связи:**\n"
        for feedback_type, count in feedback_stats['feedback_by_type'].items():
            message += f"• {feedback_type}: {count}\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error showing feedback stats: {e}")
        await update.message.reply_text(f"❌ Ошибка при получении статистики: {e}")

async def show_ml_insights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать инсайты машинного обучения (только для админов)"""
    user = update.effective_user
    
    # Проверка на админа
    if user.id != 123456789:  # Замените на ваш Telegram ID
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    try:
        # Получаем инсайты
        insights = learning_analytics.generate_learning_insights()
        
        if not insights:
            await update.message.reply_text("💡 Пока нет новых инсайтов для улучшения")
            return
        
        message = "💡 **Инсайты для улучшения ИИ:**\n\n"
        
        for i, insight in enumerate(insights[:5], 1):  # Показываем топ-5
            message += f"**{i}. {insight.title}**\n"
            message += f"• Описание: {insight.description}\n"
            message += f"• Воздействие: {insight.impact_score:.2f}/1.0\n"
            message += f"• Уверенность: {insight.confidence:.2f}/1.0\n"
            message += f"• Ожидаемое улучшение: {insight.expected_improvement:.1f}%\n"
            message += f"• Рекомендации: {', '.join(insight.actionable_items[:2])}\n\n"
        
        # Сохраняем инсайты
        for insight in insights:
            learning_analytics.save_learning_insight(insight)
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error showing ML insights: {e}")
        await update.message.reply_text(f"❌ Ошибка при получении инсайтов: {e}")

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
    
    # Analyze speech patterns
    patterns = analyze_speech_patterns(text)
    
    # Создаем уникальный ID сессии
    session_id = f"session_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Store conversation
    if user.id not in conversation_history:
        conversation_history[user.id] = []
    
    conversation_history[user.id].append(text)
    
    # Keep only last 15 messages
    if len(conversation_history[user.id]) > 15:
        conversation_history[user.id] = conversation_history[user.id][-15:]
    
    # Анализ пользователя через систему машинного обучения
    user_analysis = ml_system.analyze_user_message(
        user_id=user.id,
        message=text,
        context=conversation_history[user.id][:-1]  # Без текущего сообщения
    )
    
    # Сбор неявной обратной связи
    feedback_system.collect_implicit_feedback(
        user_id=user.id,
        session_id=session_id,
        user_message=text,
        ai_response="",  # Будет заполнено после генерации ответа
        session_metrics={
            'response_time': 0,  # Будет заполнено
            'previous_messages': conversation_history[user.id][:-1],
            'session_length': len(conversation_history[user.id])
        }
    )
    
    # Handle cancellation
    if patterns['cancellation']:
        await update.message.reply_text(
            "Понял. Если захотите поговорить снова - просто напишите. "
            "Я всегда готов выслушать и поддержать. 💙"
        )
        # Clear user data
        user_data.pop(user.id, None)
        conversation_history.pop(user.id, None)
        return ConversationHandler.END
    
    # Handle topic change
    if patterns['topic_change']:
        await update.message.reply_text(
            "Конечно! О чем бы вы хотели поговорить? "
            "Я готов обсудить любую тему, которая вас интересует. 😊"
        )
        return WAITING_MESSAGE
    
    # Handle dream expression
    if patterns['dream_expression']:
        await update.message.reply_text(
            "🌟 Какая замечательная мечта! Это очень вдохновляюще. "
            "Расскажите, что именно вас привлекает в этом? "
            "Что вас мотивирует идти к этой цели? 😊"
        )
        return WAITING_MESSAGE
    
    # Handle self introduction request
    if patterns['self_introduction_request']:
        await update.message.reply_text(
            "Конечно! Я HR-психоаналитик и карьерный консультант. "
            "Моя работа - помогать людям понять себя, найти свой путь в жизни и карьере. "
            "Я использую методы психоанализа, чтобы лучше понять вашу личность и дать рекомендации. "
            "А теперь расскажите мне о себе! 😊"
        )
        return WAITING_MESSAGE
    
    # Handle references to previous conversation
    reference_keywords = ['мы говорили', 'говорили об этом', 'смотри выше', 'выше', 'раньше говорил', 'раньше сказал', 'об этом', 'это то что']
    is_referencing_previous = any(keyword in text.lower() for keyword in reference_keywords)
    
    if is_referencing_previous or patterns['provocative']:
        thinking_msg = await update.message.reply_text("🤔 Вспоминаю наш разговор...")
        
        # Используем полный контекст для понимания ссылки
        prompt, variant_id = get_psychology_consultation_prompt(text, user.id, conversation_history.get(user.id, []))
        response = await get_ai_response(prompt, max_tokens=300)
        
        # Записываем результат A/B теста
        quality_score = ab_testing_manager.evaluate_response_quality(text, response)
        ab_testing_manager.record_test_result(
            user_id=user.id,
            prompt_variant_id=variant_id,
            prompt_type=PromptType.PSYCHOLOGY_CONSULTATION,
            response_quality=quality_score
        )
        
        await thinking_msg.delete()
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        return WAITING_MESSAGE
    
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
    
    # Handle psychology-related questions
    if patterns['psychology_need'] or patterns['emotional_support']:
        thinking_msg = await update.message.reply_text("🤔 Анализирую вашу ситуацию...")
        
        prompt, variant_id = get_psychology_consultation_prompt(text, user.id, conversation_history.get(user.id, []))
        response = await get_ai_response(prompt, max_tokens=300)
        
        # Записываем результат A/B теста
        quality_score = ab_testing_manager.evaluate_response_quality(text, response)
        ab_testing_manager.record_test_result(
            user_id=user.id,
            prompt_variant_id=variant_id,
            prompt_type=PromptType.PSYCHOLOGY_CONSULTATION,
            response_quality=quality_score
        )
        
        # Записываем метрики обучения
        from machine_learning_system import LearningMetrics
        learning_metrics = LearningMetrics(
            user_satisfaction=0.7,  # Будет обновлено через обратную связь
            response_relevance=quality_score,
            engagement_score=min(len(text.split()) / 50.0, 1.0),
            conversion_rate=0.0,  # Будет обновлено при конверсии
            session_duration=0,  # Будет обновлено
            message_count=len(conversation_history[user.id]),
            timestamp=datetime.now()
        )
        
        ml_system.record_interaction(
            user_id=user.id,
            session_id=session_id,
            user_message=text,
            ai_response=response,
            metrics=learning_metrics
        )
        
        await thinking_msg.delete()
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
        prompt, variant_id = get_express_analysis_prompt(conversation_text, message_count, user.id)
        response = await get_ai_response(prompt, max_tokens=400)
        
        # Записываем результат A/B теста
        quality_score = ab_testing_manager.evaluate_response_quality(conversation_text, response)
        ab_testing_manager.record_test_result(
            user_id=user.id,
            prompt_variant_id=variant_id,
            prompt_type=PromptType.EXPRESS_ANALYSIS,
            response_quality=quality_score
        )
        
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
    
    # Smart AI response based on conversation and patterns
    thinking_msg = await update.message.reply_text("🤔 Думаю...")
    
    # Generate intelligent response based on patterns with full context
    conversation_text = " ".join(conversation_history[user.id][-10:])  # Last 10 messages for better context
    
    # Determine primary role based on patterns
    if patterns['dream_expression']:
        primary_role = "ВДОХНОВЛЯЮЩИЙ КОНСУЛЬТАНТ"
        focus = "поддержка мечтаний и мотивация к достижению целей"
    elif patterns['career_need'] and not patterns['psychology_need']:
        primary_role = "HR-СПЕЦИАЛИСТ"
        focus = "карьерные рекомендации и профессиональное развитие"
    elif patterns['psychology_need'] or patterns['emotional_support']:
        primary_role = "ПСИХОЛОГ"
        focus = "эмоциональная поддержка и психологическая помощь"
    else:
        primary_role = "КОНСУЛЬТАНТ"
        focus = "общее развитие и самоанализ"
    
    # Подготавливаем контекст предыдущих сообщений
    previous_context = ""
    if len(conversation_history[user.id]) > 1:
        recent_messages = conversation_history[user.id][:-1]  # все кроме текущего
        if len(recent_messages) > 8:
            recent_messages = recent_messages[-8:]  # последние 8 сообщений
        previous_context = "Предыдущие сообщения в разговоре:\n" + "\n".join([f"- {msg}" for msg in recent_messages])
    
    prompt = f"""
Ты — HR-психоаналитик и карьерный консультант. 

КОНТЕКСТ РАЗГОВОРА:
{previous_context}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{text}

ВАЖНО: Если пользователь ссылается на предыдущие части разговора, обязательно учитывай контекст выше.

АНАЛИЗ ПОЛЬЗОВАТЕЛЯ:
- Основная потребность: {focus}
- Роль: {primary_role}

ТВОИ РОЛИ (адаптивные):
1. ПСИХОЛОГ - эмпатия, поддержка, понимание эмоций
2. HR-СПЕЦИАЛИСТ - анализ личности, карьерные рекомендации  
3. КОНСУЛЬТАНТ - помощь с выбором профессии и развитием

ПРИНЦИПЫ:
- СНАЧАЛА прояви эмпатию и понимание
- ПОМНИ весь контекст разговора
- Адаптируйся к потребностям пользователя
- Поддерживай эмоционально
- Мягко подводи к самоанализу
- Если пользователь ссылается на предыдущее - обратись к контексту

ФОРМАТ: Эмпатичный ответ (1-2 предложения) + релевантный вопрос.

СТИЛЬ: Теплый, профессиональный, адаптивный к ситуации, помнящий контекст.
"""
    
    response = await get_ai_response(prompt, max_tokens=200)
    await thinking_msg.delete()
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
    application.add_handler(CommandHandler('reset', reset_bot))
    application.add_handler(CommandHandler('stats', show_ab_stats))
    application.add_handler(CommandHandler('dashboard', show_learning_dashboard))
    application.add_handler(CommandHandler('feedback', show_feedback_stats))
    application.add_handler(CommandHandler('insights', show_ml_insights))
    
    logger.info("HR-Психоаналитик запущен")
    application.run_polling()

if __name__ == "__main__":
    main()
