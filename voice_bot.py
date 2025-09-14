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
            
            # Простая симуляция распознавания на основе длительности
            if duration < 3:
                recognized_text = "Привет!"
            elif duration < 7:
                recognized_text = "Как дела? Что у тебя нового?"
            elif duration < 15:
                recognized_text = "Расскажи подробнее о своих планах и что тебя беспокоит"
            else:
                recognized_text = "Это было длинное сообщение с множеством деталей и вопросов"
            
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
        """Генерация простого ответа без внешних AI сервисов"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['привет', 'hello', 'hi']):
            return f"Привет, {user_name}! Рад вас слышать! Как дела?"
        elif any(word in text_lower for word in ['дела', 'how are you']):
            return "У меня все отлично! Работаю как AI автоответчик. А у вас как дела?"
        elif any(word in text_lower for word in ['планы', 'plans', 'что делать']):
            return "Звучит интересно! Расскажите подробнее о ваших планах."
        elif any(word in text_lower for word in ['проблема', 'беспокоит', 'trouble']):
            return "Понимаю ваше беспокойство. Я здесь, чтобы выслушать и помочь."
        elif any(word in text_lower for word in ['работа', 'work', 'job']):
            return "Работа важная тема! Что именно вас интересует в профессиональной сфере?"
        elif len(text) > 50:
            return "Спасибо за подробный рассказ! Я внимательно выслушал и готов обсудить детали."
        else:
            return f"Интересно! Получил ваше сообщение. Готов продолжить разговор, {user_name}!"

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
