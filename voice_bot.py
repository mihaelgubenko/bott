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
        """Улучшенная генерация ответов для HR-контекста"""
        text_lower = text.lower()
        
        # Профессиональные ответы для HR-бота
        if any(word in text_lower for word in ['профессии', 'карьера', 'работа', 'специальность']):
            return f"Отлично, {user_name}! Я помогу с выбором профессии. Для точного анализа рекомендую пройти полный психологический тест через команду /start. Это займет 5 минут и даст подробные рекомендации."
        elif any(word in text_lower for word in ['психологический', 'анализ', 'личности', 'тест']):
            return "Психологический анализ - моя основная специализация! Использую методики Фрейда, Юнга, MBTI и Big Five. Напишите /start чтобы начать анализ личности."
        elif any(word in text_lower for word in ['it', 'программист', 'разработчик', 'айти']):
            return "IT-сфера отличный выбор! Для определения подходящих вам IT-профессий проведу анализ ваших способностей. Начните с команды /start для персональных рекомендаций."
        elif any(word in text_lower for word in ['маркетинг', 'реклама', 'продажи']):
            return "Маркетинг требует определенного типа личности. Я проанализирую ваши коммуникативные способности и дам рекомендации. Используйте /start для начала."
        elif any(word in text_lower for word in ['сменить', 'поменять', 'другую']):
            return f"Смена профессии - серьезный шаг! Помогу определить наиболее подходящие направления исходя из вашего психотипа. {user_name}, попробуйте команду /start."
        elif any(word in text_lower for word in ['консультация', 'совет', 'помочь']):
            return "Я профессиональный HR-консультант и психоаналитик. Провожу глубокий анализ личности и даю рекомендации по карьере. Для консультации используйте /start."
        elif any(word in text_lower for word in ['привет', 'hello', 'hi']):
            return f"Привет, {user_name}! Я HR-психоаналитик, помогаю с выбором профессии и карьерным развитием. Готов провести анализ вашей личности!"
        elif any(word in text_lower for word in ['умеешь', 'можешь', 'возможности']):
            return "Мои возможности: глубокий психологический анализ, определение типа личности, рекомендации по профессиям, HR-оценка. Также тестирую функции телефонного автоответчика. Попробуйте /start или /phone."
        elif any(word in text_lower for word in ['дела', 'how are you']):
            return "Отлично работаю! Провожу психоанализ и помогаю людям найти свое призвание. А у вас как дела с карьерой?"
        elif len(text) > 50:
            return "Благодарю за подробный рассказ! Для качественного анализа и профессиональных рекомендаций предлагаю пройти полный тест. Команда /start запустит процесс."
        else:
            return f"Понял, {user_name}! Я здесь чтобы помочь с выбором профессии и анализом личности. Что вас интересует больше всего в карьерном плане?"

    async def get_ai_consultation(self, user_text: str, user_name: str, user_id: int) -> str:
        """Получение AI консультации через интегрированную телефонную систему"""
        try:
            # Пытаемся подключиться к локальному AI серверу
            import requests
            import json
            from datetime import datetime
            
            # Проверяем доступность Ollama
            try:
                ollama_response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama2",
                        "prompt": self.create_hr_prompt(user_text, user_name),
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "max_tokens": 200
                        }
                    },
                    timeout=15
                )
                
                if ollama_response.status_code == 200:
                    result = ollama_response.json()
                    ai_text = result.get('response', '').strip()
                    if ai_text:
                        logger.info(f"✅ Ollama ответ для {user_name}: {ai_text[:50]}...")
                        return self.format_telegram_response(ai_text)
                        
            except Exception as e:
                logger.warning(f"Ollama недоступен: {e}")
            
            # Fallback на OpenAI если есть ключ
            if hasattr(self, 'openai_client'):
                try:
                    openai_response = await self.get_openai_response(user_text, user_name)
                    if openai_response:
                        return self.format_telegram_response(openai_response)
                except Exception as e:
                    logger.warning(f"OpenAI недоступен: {e}")
            
            # Fallback на улучшенный локальный AI
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
            import openai
            import os
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == "dummy_key_for_testing":
                return None
                
            openai.api_key = api_key
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": f"Ты HR-консультант Анна. Пользователь {user_name} отправил голосовое сообщение. Дай краткую профессиональную консультацию по карьере (2-3 предложения)."
                    },
                    {
                        "role": "user", 
                        "content": user_text
                    }
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
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
