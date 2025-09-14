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
            
            # Простой AI ответ
            ai_response = await self.generate_simple_response(recognized_text, user.first_name)
            
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
