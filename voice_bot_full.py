#!/usr/bin/env python3
"""
Расширение для main.py: добавляет обработку голосовых сообщений
Интегрируется с TinyLlama автоответчиком
"""
import logging
import os
import requests
import tempfile
import subprocess
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

# Импортируем наш AI автоответчик
import sys
sys.path.append('.')

logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        self.ai_server_url = "http://localhost:8765"  # WebSocket сервер
        self.simple_api_url = "http://localhost:8001"  # Простой API
        self.ollama_path = r'C:\Users\mihae\AppData\Local\Programs\Ollama\ollama.exe'
        
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых сообщений"""
        user = update.effective_user
        voice = update.message.voice
        
        logger.info(f"📢 Получено голосовое сообщение от {user.first_name} (ID: {user.id})")
        
        # Уведомляем пользователя
        status_msg = await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
        
        try:
            # Скачиваем голосовое сообщение
            voice_file = await context.bot.get_file(voice.file_id)
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as tmp_file:
                await voice_file.download_to_drive(tmp_file.name)
                voice_path = tmp_file.name
            
            # Конвертируем в WAV (если нужно)
            wav_path = voice_path.replace(".oga", ".wav")
            try:
                # Используем ffmpeg для конвертации (если установлен)
                subprocess.run([
                    'ffmpeg', '-i', voice_path, '-ar', '16000', '-ac', '1', wav_path
                ], check=True, capture_output=True)
                audio_path = wav_path
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Если ffmpeg недоступен, используем исходный файл
                audio_path = voice_path
            
            # Симулируем распознавание речи (заглушка)
            recognized_text = await self.simulate_speech_recognition(audio_path)
            
            await status_msg.edit_text(f"🎤 Распознано: \"{recognized_text}\"\n\n🤖 AI обрабатывает...")
            
            # Отправляем в AI для обработки
            ai_response = await self.get_ai_response(recognized_text, user.id)
            
            # Отвечаем пользователю
            await status_msg.edit_text(
                f"🎤 **Ваше сообщение:** {recognized_text}\n\n"
                f"🤖 **AI ответ:** {ai_response}"
            )
            
            # Генерируем голосовой ответ (если возможно)
            try:
                voice_response = await self.generate_voice_response(ai_response)
                if voice_response:
                    await update.message.reply_voice(voice_response)
            except Exception as e:
                logger.warning(f"Не удалось создать голосовой ответ: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки голосового сообщения: {e}")
            await status_msg.edit_text(
                "❌ Извините, не удалось обработать голосовое сообщение. "
                "Попробуйте отправить текстом."
            )
        finally:
            # Удаляем временные файлы
            try:
                if 'voice_path' in locals():
                    os.unlink(voice_path)
                if 'wav_path' in locals() and os.path.exists(wav_path):
                    os.unlink(wav_path)
            except:
                pass
    
    async def simulate_speech_recognition(self, audio_path):
        """Симуляция распознавания речи"""
        # Список возможных фраз для симуляции
        sample_phrases = [
            "Привет, как дела?",
            "Что ты умеешь делать?",
            "Расскажи о себе",
            "Как тебя зовут?",
            "Какая сегодня погода?",
            "Помоги мне с выбором профессии",
            "Проведи анализ личности",
            "Спасибо за помощь",
            "До свидания"
        ]
        
        # Определяем фразу по размеру файла (простая симуляция)
        try:
            file_size = os.path.getsize(audio_path)
            phrase_index = file_size % len(sample_phrases)
            return sample_phrases[phrase_index]
        except:
            return "Пользователь что-то сказал"
    
    async def get_ai_response(self, text, user_id):
        """Получение ответа от AI автоответчика"""
        try:
            # Пробуем простой API
            response = requests.post(
                f"{self.simple_api_url}/chat",
                json={"message": text, "caller_id": str(user_id)},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "Спасибо за сообщение!")
            else:
                raise Exception(f"API error: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Ошибка API: {e}, используем прямой вызов Ollama")
            
            # Прямой вызов TinyLlama
            try:
                prompt = f"Ответь кратко как дружелюбный помощник: {text}"
                result = subprocess.run([
                    self.ollama_path, 'run', 'tinyllama', prompt
                ], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore')
                
                if result.returncode == 0:
                    response = result.stdout.strip()
                    # Ограничиваем ответ
                    if len(response) > 200:
                        response = response[:200] + "..."
                    return response if response else "Понял вас!"
                else:
                    return "Извините, сейчас не могу ответить. Попробуйте текстом."
                    
            except Exception as e2:
                logger.error(f"Ошибка Ollama: {e2}")
                return "Спасибо за голосовое сообщение! Попробуйте написать текстом."
    
    async def generate_voice_response(self, text):
        """Генерация голосового ответа"""
        try:
            # Проверяем доступность espeak
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None
            
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                wav_path = tmp_file.name
            
            # Используем espeak для синтеза речи
            subprocess.run([
                'espeak', 
                '-s', '150',      # скорость
                '-v', 'ru',       # русский голос
                '-w', wav_path,   # выходной файл
                text[:100]        # ограничиваем длину
            ], check=True, timeout=10)
            
            # Читаем и возвращаем аудио
            with open(wav_path, 'rb') as f:
                audio_data = f.read()
            
            # Удаляем временный файл
            os.unlink(wav_path)
            
            return audio_data
            
        except Exception as e:
            logger.warning(f"Ошибка генерации голоса: {e}")
            return None

# Глобальный экземпляр обработчика
voice_handler = VoiceHandler()

# Функция для добавления в main.py
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений для интеграции в main.py"""
    await voice_handler.handle_voice_message(update, context)

# Обработчик для видео-сообщений (круглые видео)
async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка круглых видео-сообщений"""
    user = update.effective_user
    await update.message.reply_text(
        f"🎥 {user.first_name}, я пока не умею обрабатывать видео-сообщения. "
        "Отправьте голосовое сообщение или напишите текстом!"
    )

# Тестовая функция
async def test_voice_system():
    """Тестирование голосовой системы"""
    handler = VoiceHandler()
    
    # Тест AI ответа
    test_text = "Привет, как дела?"
    response = await handler.get_ai_response(test_text, 12345)
    print(f"Тест AI: '{test_text}' -> '{response}'")
    
    # Тест генерации голоса
    voice_data = await handler.generate_voice_response("Привет! Как дела?")
    if voice_data:
        print(f"Голосовой ответ сгенерирован: {len(voice_data)} байт")
    else:
        print("Голосовой ответ не сгенерирован")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_voice_system())
