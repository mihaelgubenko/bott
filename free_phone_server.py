#!/usr/bin/env python3
"""
🎤 Бесплатная WebSocket телефонная система для HR-Психоаналитика
Использует Ollama + WebRTC + Browser APIs для реальных звонков
"""
import asyncio
import websockets
import json
import logging
import base64
import tempfile
import os
from datetime import datetime
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama2"  # Или другая загруженная модель
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
USE_OLLAMA = True  # Приоритет Ollama, fallback на OpenAI

class FreePhoneServer:
    """Бесплатный телефонный сервер с AI"""
    
    def __init__(self):
        self.active_calls = {}
        self.total_calls = 0
        logger.info("🚀 Запуск бесплатного телефонного сервера...")
    
    async def check_ollama_connection(self):
        """Проверка подключения к Ollama"""
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [m['name'] for m in models]
                logger.info(f"✅ Ollama подключен. Доступные модели: {available_models}")
                return True, available_models
        except Exception as e:
            logger.warning(f"⚠️ Ollama недоступен: {e}")
            return False, []
    
    async def generate_ai_response(self, user_input: str, user_id: str = "unknown") -> str:
        """Генерация AI ответа через Ollama или OpenAI"""
        try:
            # Проверяем Ollama
            if USE_OLLAMA:
                ollama_available, models = await self.check_ollama_connection()
                if ollama_available and OLLAMA_MODEL in [m.split(':')[0] for m in models]:
                    return await self.ollama_response(user_input)
            
            # Fallback на OpenAI
            if OPENAI_API_KEY and OPENAI_API_KEY != "dummy_key_for_testing":
                return await self.openai_response(user_input)
            
            # Fallback на локальный AI
            return await self.local_ai_response(user_input)
            
        except Exception as e:
            logger.error(f"Ошибка генерации AI ответа: {e}")
            return "Извините, возникла техническая проблема. Попробуйте переформулировать вопрос."
    
    async def ollama_response(self, user_input: str) -> str:
        """Ответ через Ollama"""
        try:
            # Системный промпт для HR-консультанта
            system_prompt = """Ты профессиональный HR-консультант и психоаналитик по имени Анна. 
Твоя задача - помочь людям с выбором профессии и карьерным развитием.
Используй методики психологического анализа.
Отвечай кратко, дружелюбно и профессионально на русском языке.
Максимум 2-3 предложения за раз."""
            
            full_prompt = f"{system_prompt}\n\nВопрос клиента: {user_input}\n\nОтвет:"
            
            data = {
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 150
                }
            }
            
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_text = result.get('response', '').strip()
                logger.info(f"✅ Ollama ответ: {ai_text[:50]}...")
                return ai_text if ai_text else await self.local_ai_response(user_input)
            else:
                logger.error(f"Ollama ошибка: {response.status_code}")
                return await self.local_ai_response(user_input)
                
        except Exception as e:
            logger.error(f"Ошибка Ollama: {e}")
            return await self.local_ai_response(user_input)
    
    async def openai_response(self, user_input: str) -> str:
        """Ответ через OpenAI API"""
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты HR-консультант Анна. Помогаешь с выбором профессии. Отвечай кратко и профессионально."},
                    {"role": "user", "content": user_input}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            ai_text = response.choices[0].message.content.strip()
            logger.info(f"✅ OpenAI ответ: {ai_text[:50]}...")
            return ai_text
            
        except Exception as e:
            logger.error(f"Ошибка OpenAI: {e}")
            return await self.local_ai_response(user_input)
    
    async def local_ai_response(self, user_input: str) -> str:
        """Локальный AI без внешних сервисов"""
        input_lower = user_input.lower()
        
        # HR-специфичные ответы
        if any(word in input_lower for word in ['профессия', 'работа', 'карьера', 'специальность']):
            return "Отличный вопрос о карьере! Какая сфера вас больше интересует: IT, маркетинг, медицина или что-то другое?"
            
        elif any(word in input_lower for word in ['it', 'программирование', 'айти', 'компьютеры']):
            return "IT-сфера очень перспективна! Есть разработка, тестирование, аналитика. Что вам ближе?"
            
        elif any(word in input_lower for word in ['маркетинг', 'реклама', 'продажи']):
            return "Маркетинг требует креативности и коммуникации. Вас интересует стратегия, креатив или аналитика?"
            
        elif any(word in input_lower for word in ['психология', 'анализ', 'тест']):
            return "Психологический анализ - моя специализация! Рекомендую пройти полный тест в нашем Telegram-боте."
            
        elif any(word in input_lower for word in ['зарплата', 'деньги', 'доход']):
            return "Высокие доходы в IT, финансах, медицине. Но главное - найти дело по душе. Что вас увлекает?"
            
        elif any(word in input_lower for word in ['сменить', 'поменять']):
            return "Смена профессии возможна! Расскажите, что именно не устраивает в текущей работе?"
            
        elif any(word in input_lower for word in ['привет', 'здравствуйте']):
            return "Привет! Я Анна, ваш AI-консультант по карьере. Помогу выбрать подходящую профессию!"
            
        elif any(word in input_lower for word in ['спасибо', 'благодарю']):
            return "Пожалуйста! Для детального анализа попробуйте наш Telegram-бот. Удачи в карьере!"
            
        else:
            return "Понимаю ваш вопрос. Расскажите подробнее о ваших интересах и целях в карьере?"

    async def handle_client(self, websocket, path):
        """Обработка WebSocket подключений от браузера"""
        client_id = f"client_{self.total_calls}"
        self.total_calls += 1
        
        logger.info(f"📞 Новое подключение: {client_id} ({websocket.remote_address})")
        
        self.active_calls[client_id] = {
            "websocket": websocket,
            "start_time": datetime.now(),
            "status": "connected",
            "messages": []
        }
        
        try:
            # Приветственное сообщение
            welcome_msg = {
                "type": "ai_response",
                "text": "Добро пожаловать в HR консультационный центр! Меня зовут Анна, ваш AI-консультант по карьере. Как дела? Чем могу помочь с выбором профессии?",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Основной цикл обработки сообщений
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(client_id, data)
                except json.JSONDecodeError:
                    logger.error(f"Некорректный JSON от {client_id}")
                except Exception as e:
                    logger.error(f"Ошибка обработки сообщения от {client_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔚 Соединение закрыто: {client_id}")
        except Exception as e:
            logger.error(f"Ошибка соединения {client_id}: {e}")
        finally:
            # Очистка
            if client_id in self.active_calls:
                del self.active_calls[client_id]
    
    async def process_message(self, client_id: str, data: dict):
        """Обработка сообщения от клиента"""
        message_type = data.get("type", "")
        websocket = self.active_calls[client_id]["websocket"]
        
        if message_type == "audio_data":
            # Обработка аудио (симуляция STT)
            audio_data = data.get("audio", "")
            recognized_text = await self.simulate_speech_recognition(audio_data)
            
            # Отправляем распознанный текст
            stt_response = {
                "type": "speech_recognized",
                "text": recognized_text,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(stt_response))
            
            # Генерируем AI ответ
            ai_response = await self.generate_ai_response(recognized_text, client_id)
            
            # Отправляем AI ответ
            ai_msg = {
                "type": "ai_response", 
                "text": ai_response,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(ai_msg))
            
            # Сохраняем в истории
            self.active_calls[client_id]["messages"].extend([
                {"role": "user", "text": recognized_text},
                {"role": "ai", "text": ai_response}
            ])
            
        elif message_type == "text_message":
            # Обработка текстового сообщения
            user_text = data.get("text", "")
            ai_response = await self.generate_ai_response(user_text, client_id)
            
            response = {
                "type": "ai_response",
                "text": ai_response,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response))
            
        elif message_type == "ping":
            # Проверка соединения
            pong = {
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(pong))
    
    async def simulate_speech_recognition(self, audio_data: str) -> str:
        """Симуляция распознавания речи (в будущем - реальный STT)"""
        # Простая симуляция на основе длины аудио
        audio_length = len(audio_data) if audio_data else 0
        
        professional_phrases = [
            "Хочу обсудить выбор профессии",
            "Помогите определиться с карьерой",
            "Какие профессии в IT популярны", 
            "Интересует работа в маркетинге",
            "Хочу сменить сферу деятельности",
            "Проведите анализ моих способностей"
        ]
        
        casual_phrases = [
            "Привет, как дела?",
            "Что ты умеешь делать?",
            "Расскажи о себе",
            "Спасибо за помощь"
        ]
        
        import random
        if audio_length > 1000:  # "Длинные" сообщения
            return random.choice(professional_phrases)
        else:
            return random.choice(casual_phrases)

async def main():
    """Запуск сервера"""
    server = FreePhoneServer()
    
    # Проверяем Ollama при запуске
    await server.check_ollama_connection()
    
    logger.info("🎤 Запуск WebSocket сервера на ws://localhost:8765")
    logger.info("🌐 Откройте browser_phone.html для тестирования")
    
    # Запуск WebSocket сервера (для Railway)
    port = int(os.getenv("PORT", 8765))
    host = "0.0.0.0" if os.getenv("RAILWAY_ENVIRONMENT") else "localhost"
    
    start_server = websockets.serve(
        server.handle_client, 
        host, 
        port,
        ping_interval=20,
        ping_timeout=10
    )
    
    await start_server
    logger.info("✅ Сервер запущен! Ожидание подключений...")
    
    # Держим сервер активным
    await asyncio.Future()  # Бесконечное ожидание

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
