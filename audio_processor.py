#!/usr/bin/env python3
"""
Обработка аудио для автоответчика
Включает Speech-to-Text и Text-to-Speech
"""
import subprocess
import tempfile
import os
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        # Пути к инструментам (пока используем заглушки)
        self.espeak_available = self.check_espeak()
        
    def check_espeak(self):
        """Проверяем доступность espeak для TTS"""
        try:
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    async def speech_to_text(self, audio_data_base64):
        """
        Конвертация речи в текст
        Пока что симуляция - в будущем можно добавить Whisper.cpp
        """
        try:
            # Декодируем base64 аудио
            audio_bytes = base64.b64decode(audio_data_base64)
            
            # Симуляция обработки аудио
            logger.info(f"🎤 Получено аудио: {len(audio_bytes)} байт")
            
            # В реальности здесь будет Whisper.cpp или другой STT
            simulated_texts = [
                "Алло, здравствуйте!",
                "Можно поговорить с директором?",
                "Какой у вас режим работы?",
                "Сколько стоят ваши услуги?",
                "Спасибо, до свидания!"
            ]
            
            # Выбираем случайный текст на основе размера аудио
            text_index = len(audio_bytes) % len(simulated_texts)
            recognized_text = simulated_texts[text_index]
            
            logger.info(f"📝 Распознано: {recognized_text}")
            return recognized_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка STT: {e}")
            return "Извините, не понял вас"
    
    async def text_to_speech(self, text):
        """
        Конвертация текста в речь
        """
        try:
            if not self.espeak_available:
                # Если espeak недоступен, возвращаем заглушку
                logger.warning("⚠️ espeak недоступен, возвращаем пустое аудио")
                return self.create_silence_audio()
            
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_audio_path = tmp_file.name
            
            # Используем espeak для синтеза речи
            cmd = [
                'espeak',
                '-s', '150',  # скорость
                '-v', 'ru',   # русский голос
                '-w', tmp_audio_path,  # выходной файл
                text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(tmp_audio_path):
                # Читаем аудио файл
                with open(tmp_audio_path, "rb") as f:
                    audio_data = f.read()
                
                # Удаляем временный файл
                os.unlink(tmp_audio_path)
                
                # Кодируем в base64
                audio_base64 = base64.b64encode(audio_data).decode()
                
                logger.info(f"🔊 TTS сгенерировано: {len(audio_data)} байт")
                return audio_base64
            else:
                logger.error(f"❌ espeak error: {result.stderr}")
                return self.create_silence_audio()
                
        except Exception as e:
            logger.error(f"❌ Ошибка TTS: {e}")
            return self.create_silence_audio()
    
    def create_silence_audio(self):
        """Создает короткий фрагмент тишины как заглушку"""
        # Простой WAV заголовок + тишина (44 байта заголовок + 1000 байт тишины)
        wav_header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        silence_data = b'\x00' * 1000
        audio_data = wav_header + silence_data
        return base64.b64encode(audio_data).decode()

# Глобальный экземпляр процессора
audio_processor = AudioProcessor()

# Функции для использования в других модулях
async def process_audio_to_text(audio_base64):
    """Удобная функция для STT"""
    return await audio_processor.speech_to_text(audio_base64)

async def process_text_to_audio(text):
    """Удобная функция для TTS"""
    return await audio_processor.text_to_speech(text)

def get_audio_info():
    """Информация о доступных аудио возможностях"""
    return {
        "espeak_available": audio_processor.espeak_available,
        "stt_engine": "simulated",
        "tts_engine": "espeak" if audio_processor.espeak_available else "simulated"
    }
