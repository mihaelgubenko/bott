#!/usr/bin/env python3
"""
Упрощенная версия голосового обработчика без сложных зависимостей
Для деплоя на Railway
"""
import logging
import tempfile
import os
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class SimpleVoiceHandler:
    def __init__(self):
        logger.info("🎤 Инициализация упрощенного голосового обработчика")
        
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Упрощенная обработка голосовых сообщений"""
        user = update.effective_user
        voice = update.message.voice
        
        logger.info(f"📢 Голосовое сообщение от {user.first_name} (ID: {user.id})")
        
        # Уведомляем пользователя
        status_msg = await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
        
        try:
            # Симулируем обработку
            duration = voice.duration if voice.duration else 5
            
            # Улучшенная симуляция с профессиональным контекстом
            import random
            
            professional_phrases = [
                "Хочу обсудить профессии и карьеру",
                "Помогите с выбором специальности", 
                "Проведите психологический анализ",
                "Какие профессии мне подходят",
                "Ищу работу в IT сфере",
                "Интересует маркетинг и реклама",
                "Хочу сменить профессию",
                "Нужна консультация по карьере"
            ]
            
            casual_phrases = [
                "Привет, как дела?",
                "Что ты умеешь делать?", 
                "Расскажи о своих возможностях",
                "Можешь помочь с вопросом?",
                "Спасибо за помощь"
            ]
            
            if duration > 10:  # Длинные сообщения = профессиональные
                recognized_text = random.choice(professional_phrases)
            elif duration > 5:  # Средние = вопросы
                recognized_text = "Расскажи подробнее о том что ты умеешь и как можешь помочь"
            else:  # Короткие = приветствия
                recognized_text = random.choice(casual_phrases)
            
            # AI ответ через интегрированную телефонную систему
            ai_response = await self.get_ai_consultation(recognized_text, user.first_name, user.id)
            
            # Отвечаем пользователю
            await status_msg.edit_text(
                f"🎤 **Ваше сообщение:** {recognized_text}\n\n"
                f"🤖 **AI ответ:** {ai_response}\n\n"
                f"⏱️ **Длительность:** {duration} сек.\n"
                f"💡 *Это симуляция - для полной версии нужны дополнительные API*"
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки голосового сообщения: {e}")
            await status_msg.edit_text(
                "❌ Извините, не удалось обработать голосовое сообщение.\n\n"
                "🎤 Попробуйте еще раз или отправьте текстом.\n\n"
                "💡 Для полной поддержки голоса требуется настройка дополнительных сервисов."
            )
    
    async def generate_simple_response(self, text, user_name):
        """Улучшенная генерация ответов для HR-контекста (Умный локальный AI)"""
        text_lower = text.lower()
        
        # Расширенные профессиональные ответы для HR-бота
        if any(word in text_lower for word in ['профессии', 'карьера', 'работа', 'специальность']):
            responses = [
                f"Отлично, {user_name}! Выбор профессии - важнейшее решение. Рассмотрим ваши интересы, способности и склонности. Какая сфера вас больше привлекает: творческая, техническая, работа с людьми или аналитическая?",
                f"Понимаю ваш интерес к карьере, {user_name}. Современный рынок труда предлагает множество возможностей. Расскажите, что вам нравится делать больше всего?",
                f"Замечательно, что думаете о карьере! Для точных рекомендаций важно понять ваш психотип. Пройдите полный анализ через /start - это даст детальные персональные советы."
            ]
            import random
            return random.choice(responses)
            
        elif any(word in text_lower for word in ['it', 'программист', 'разработчик', 'айти', 'компьютер']):
            return f"IT-сфера очень перспективна, {user_name}! Есть множество направлений: фронтенд-разработка (создание интерфейсов), бэкенд (серверная логика), data science (анализ данных), DevOps (инфраструктура). Что вас больше привлекает - создавать то, что видят пользователи, или работать с данными и алгоритмами?"
            
        elif any(word in text_lower for word in ['маркетинг', 'реклама', 'продажи', 'smm']):
            return f"Маркетинг - динамичная сфера! Включает стратегическое планирование, креативную разработку, аналитику данных, работу с соцсетями. {user_name}, вас больше привлекает творческая составляющая (создание контента) или аналитическая (изучение метрик и поведения клиентов)?"
            
        elif any(word in text_lower for word in ['сменить', 'поменять', 'другую', 'новую']):
            return f"Смена профессии в любом возрасте - это нормально и часто приводит к успеху! {user_name}, расскажите: что именно не устраивает в текущей работе? Это поможет найти то, что действительно подойдет. Монотонность? Мало общения? Низкая зарплата? Отсутствие развития?"
            
        elif any(word in text_lower for word in ['образование', 'учиться', 'курсы', 'университет']):
            return f"Образование - отличная инвестиция в будущее! Сейчас много вариантов: университеты, онлайн-курсы, практические интенсивы. {user_name}, важно выбрать направление, которое соответствует вашему типу личности. Для персональных рекомендаций пройдите тест /start."
            
        elif any(word in text_lower for word in ['зарплата', 'деньги', 'доход', 'заработок']):
            return f"Финансовая мотивация важна! Высокооплачиваемые сферы: IT (от 100k), финансы и банки (от 80k), медицина (от 70k), консалтинг (от 90k). Но помните, {user_name} - работа должна приносить удовольствие. Что вас больше мотивирует: высокий доход или интересные задачи?"
            
        elif any(word in text_lower for word in ['творчество', 'творческ', 'дизайн', 'искусство']):
            return f"Творческие профессии очень разнообразны! Графический дизайн, UX/UI, архитектура, реклама, фотография, видеопродакшн, писательство. {user_name}, что вас больше вдохновляет - визуальное искусство, работа с текстом или создание пользовательского опыта?"
            
        elif any(word in text_lower for word in ['консультация', 'совет', 'помочь', 'помощь']):
            return f"Конечно помогу с профессиональной консультацией! Я анализирую личность по методикам Фрейда, Юнга, MBTI и даю конкретные рекомендации. {user_name}, для качественного анализа лучше пройти полный тест /start - это займет 5 минут, но даст точные результаты."
            
        elif any(word in text_lower for word in ['психология', 'анализ', 'личности', 'тест', 'mbti']):
            return "Психологический анализ - моя основная специализация! Использую современные методики: MBTI для определения типа личности, Big Five для анализа черт характера, методы Фрейда и Юнга для глубинного понимания мотивов. Начните анализ командой /start!"
            
        elif any(word in text_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
            return f"Привет, {user_name}! Я Анна - ваш персональный HR-консультант и психоаналитик. Помогаю людям найти идеальную профессию на основе глубокого анализа личности. Готова провести анализ ваших способностей и дать рекомендации по карьере!"
            
        elif any(word in text_lower for word in ['умеешь', 'можешь', 'возможности', 'функции']):
            return "Мои возможности обширны: провожу глубокий психологический анализ личности, определяю тип по MBTI, анализирую черты характера, даю персональные рекомендации по профессиям, помогаю с карьерным планированием. Также тестирую голосовые функции для телефонных консультаций. Попробуйте /start для полного анализа!"
            
        elif any(word in text_lower for word in ['дела', 'настроение', 'жизнь']):
            return f"У меня отлично! Помогаю людям находить свое призвание и строить успешную карьеру. Это очень вдохновляющая работа! А у вас как дела с профессиональной самореализацией, {user_name}? Довольны ли текущей работой?"
            
        elif any(word in text_lower for word in ['бухгалтер', 'финансы', 'экономика', 'банк']):
            return f"Финансовая сфера предлагает много возможностей! Помимо классической бухгалтерии есть: финансовый анализ, аудит, налоговое консультирование, банковское дело, инвестиции. {user_name}, что вас больше привлекает - работа с цифрами и отчетностью или консультирование клиентов?"
            
        elif len(text) > 80:
            return f"Благодарю за подробный рассказ, {user_name}! Вижу, что вопрос карьеры для вас важен. Для качественного анализа и конкретных рекомендаций рекомендую пройти полный психологический тест - команда /start запустит процесс. Это займет 5-7 минут, но даст точные персональные советы."
            
        else:
            responses = [
                f"Понял вас, {user_name}! Я здесь, чтобы помочь с выбором профессии и анализом личности. Расскажите, что вас больше всего интересует в карьерном плане?",
                f"Отлично, что обратились за консультацией! Какие вопросы о карьере и профессиональном развитии вас волнуют, {user_name}?",
                f"Готов помочь с профессиональным самоопределением! Что хотели бы узнать о своих карьерных возможностях?"
            ]
            import random
            return random.choice(responses)

    async def get_ai_consultation(self, user_text: str, user_name: str, user_id: int) -> str:
        """Получение AI консультации через интегрированную телефонную систему"""
        try:
            import requests
            import json
            import os
            from datetime import datetime
            
            # Приоритет OpenAI для Railway (облачный деплой)
            railway_env = os.getenv('RAILWAY_ENVIRONMENT')
            if railway_env:
                logger.info("🚀 Railway среда: используем OpenAI API")
                try:
                    openai_response = await self.get_openai_response(user_text, user_name)
                    if openai_response:
                        return self.format_telegram_response(openai_response)
                except Exception as e:
                    logger.warning(f"OpenAI недоступен в Railway: {e}")
            
            # Для локальной разработки - пробуем Ollama
            try:
                ollama_response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "tinyllama:latest",
                        "prompt": self.create_hr_prompt(user_text, user_name),
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 100
                        }
                    },
                    timeout=10  # Уменьшили timeout для Railway
                )
                
                if ollama_response.status_code == 200:
                    result = ollama_response.json()
                    ai_text = result.get('response', '').strip()
                    if ai_text:
                        logger.info(f"✅ Ollama ответ для {user_name}: {ai_text[:50]}...")
                        return self.format_telegram_response(ai_text)
                        
            except Exception as e:
                logger.warning(f"Ollama недоступен: {e}")
            
            # Fallback на OpenAI если Ollama не работает
            try:
                openai_response = await self.get_openai_response(user_text, user_name)
                if openai_response:
                    return self.format_telegram_response(openai_response)
            except Exception as e:
                logger.warning(f"OpenAI недоступен: {e}")
            
            # Финальный fallback на локальный AI
            return await self.generate_simple_response(user_text, user_name)
            
        except Exception as e:
            logger.error(f"Ошибка AI консультации: {e}")
            return f"Понял ваш вопрос, {user_name}! Для детального анализа рекомендую использовать команду /start для полного психологического теста."

    def create_hr_prompt(self, user_text: str, user_name: str) -> str:
        """Создание промпта для HR-консультации"""
        return f"""Ты профессиональный HR-консультант и психоаналитик Анна.

КОНТЕКСТ: Пользователь {user_name} отправил голосовое сообщение в Telegram боте для HR-психоанализа.

ЗАДАЧА: Дай профессиональную консультацию по карьере и выбору профессии.

СТИЛЬ ОТВЕТА:
- Дружелюбный но профессиональный тон
- 2-3 предложения максимум
- Конкретные рекомендации
- При необходимости направляй на полный тест

ВОПРОС ПОЛЬЗОВАТЕЛЯ: "{user_text}"

ОТВЕТ:"""

    def format_telegram_response(self, ai_text: str) -> str:
        """Форматирование ответа для Telegram"""
        # Ограничиваем длину для читаемости
        if len(ai_text) > 300:
            ai_text = ai_text[:297] + "..."
            
        # Добавляем emoji и структуру
        formatted_response = f"🤖 **AI-консультант:**\n\n{ai_text}\n\n💡 *Для полного анализа личности используйте /start*"
        
        return formatted_response

    async def get_openai_response(self, user_text: str, user_name: str) -> str:
        """Получение ответа от OpenAI API"""
        try:
            import os
            import requests
            import json
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == "dummy_key_for_testing" or not api_key.startswith('sk-'):
                logger.warning(f"OpenAI API ключ некорректный: {api_key[:10] if api_key else 'None'}...")
                return None
                
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system", 
                        "content": f"Ты HR-консультант Анна. Пользователь {user_name} отправил голосовое сообщение. Дай краткую профессиональную консультацию по карьере (2-3 предложения)."
                    },
                    {
                        "role": "user", 
                        "content": user_text
                    }
                ],
                "max_tokens": 150,
                "temperature": 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_text = result['choices'][0]['message']['content'].strip()
                logger.info(f"✅ OpenAI ответ для {user_name}: {ai_text[:50]}...")
                return ai_text
            else:
                logger.error(f"OpenAI API ошибка {response.status_code}: {response.text}")
                return None
            
        except Exception as e:
            logger.error(f"Ошибка OpenAI: {e}")
            return None

    async def handle_video_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка круглых видео-сообщений"""
        user = update.effective_user
        video_note = update.message.video_note
        
        logger.info(f"🎥 Видео-сообщение от {user.first_name} (ID: {user.id})")
        
        duration = video_note.duration if video_note.duration else 0
        
        await update.message.reply_text(
            f"🎥 **Получил видео-сообщение!**\n\n"
            f"⏱️ Длительность: {duration} сек.\n"
            f"👤 От: {user.first_name}\n\n"
            f"🤖 В текущей версии я обрабатываю только голосовые сообщения.\n"
            f"📱 Попробуйте отправить голосовое сообщение или напишите текстом!\n\n"
            f"💡 *Обработка видео будет добавлена в следующих версиях*"
        )

# Глобальный экземпляр обработчика
voice_handler = SimpleVoiceHandler()

# Функции для экспорта в main.py
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений для интеграции в main.py"""
    await voice_handler.handle_voice_message(update, context)

async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик видео-сообщений для интеграции в main.py"""
    await voice_handler.handle_video_note(update, context)

# Функция тестирования
async def test_voice_system():
    """Тестирование голосовой системы"""
    print("🧪 Тестирование упрощенной голосовой системы...")
    
    handler = SimpleVoiceHandler()
    
    # Тест генерации ответов
    test_phrases = [
        "Привет, как дела?",
        "Что у меня с планами на работе",
        "У меня проблемы с проектом",
        "Длинное сообщение с множеством деталей о том что происходит в жизни"
    ]
    
    for phrase in test_phrases:
        response = await handler.generate_simple_response(phrase, "Тестер")
        print(f"📝 '{phrase}' -> '{response}'")
    
    print("✅ Тестирование завершено")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_voice_system())
