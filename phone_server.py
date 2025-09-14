#!/usr/bin/env python3
"""
WebSocket сервер для телефонного автоответчика
Поддерживает real-time обработку звонков с AI
"""
import asyncio
import websockets
import json
import subprocess
import tempfile
import os
import base64
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PhoneAutoresponder:
    def __init__(self):
        self.ollama_path = r'C:\Users\mihae\AppData\Local\Programs\Ollama\ollama.exe'
        self.model = "tinyllama"
        self.active_calls = {}
        
    async def handle_client(self, websocket):
        """Обработчик WebSocket соединений"""
        client_id = f"client_{datetime.now().strftime('%H%M%S')}"
        logger.info(f"📞 Новое подключение: {client_id}")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                await self.process_message(websocket, client_id, data)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"📴 Соединение закрыто: {client_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в соединении {client_id}: {e}")
            await self.send_error(websocket, str(e))

    async def process_message(self, websocket, client_id, data):
        """Обработка сообщений от клиента"""
        message_type = data.get("type")
        
        if message_type == "call_start":
            await self.handle_call_start(websocket, client_id, data)
        elif message_type == "audio_data":
            await self.handle_audio_data(websocket, client_id, data)
        elif message_type == "text_message":
            await self.handle_text_message(websocket, client_id, data)
        elif message_type == "call_end":
            await self.handle_call_end(websocket, client_id, data)
        else:
            await self.send_error(websocket, f"Unknown message type: {message_type}")

    async def handle_call_start(self, websocket, client_id, data):
        """Обработка начала звонка"""
        caller_id = data.get("caller_id", "Unknown")
        self.active_calls[client_id] = {
            "caller_id": caller_id,
            "start_time": datetime.now(),
            "messages": []
        }
        
        logger.info(f"📞 Звонок начат: {caller_id} -> {client_id}")
        
        # Отправляем приветствие
        welcome_text = "Здравствуйте! Вы говорите с AI автоответчиком. Чем могу помочь?"
        
        response = {
            "type": "ai_response",
            "text": welcome_text,
            "caller_id": caller_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send(json.dumps(response))

    async def handle_text_message(self, websocket, client_id, data):
        """Обработка текстовых сообщений (для тестирования)"""
        user_text = data.get("text", "")
        caller_id = data.get("caller_id", "test")
        
        if not user_text:
            await self.send_error(websocket, "Empty message")
            return
        
        logger.info(f"💬 Текст от {caller_id}: {user_text}")
        
        # Записываем в историю
        if client_id in self.active_calls:
            self.active_calls[client_id]["messages"].append({
                "type": "user",
                "text": user_text,
                "timestamp": datetime.now()
            })
        
        # Обрабатываем через AI
        ai_response = await self.process_with_ai(user_text, caller_id)
        
        # Записываем ответ AI
        if client_id in self.active_calls:
            self.active_calls[client_id]["messages"].append({
                "type": "ai",
                "text": ai_response,
                "timestamp": datetime.now()
            })
        
        response = {
            "type": "ai_response",
            "text": ai_response,
            "caller_id": caller_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send(json.dumps(response))

    async def handle_audio_data(self, websocket, client_id, data):
        """Обработка аудио данных (заглушка для будущего)"""
        # Пока что симулируем обработку аудио
        audio_base64 = data.get("audio", "")
        caller_id = data.get("caller_id", "unknown")
        
        logger.info(f"🎤 Получено аудио от {caller_id} (размер: {len(audio_base64)} символов)")
        
        # Симулируем распознавание речи
        simulated_text = "Пользователь что-то сказал"
        
        # Обрабатываем как текст
        ai_response = await self.process_with_ai(simulated_text, caller_id)
        
        response = {
            "type": "ai_response", 
            "text": ai_response,
            "caller_id": caller_id,
            "timestamp": datetime.now().isoformat(),
            "note": "Audio processing simulated"
        }
        
        await websocket.send(json.dumps(response))

    async def handle_call_end(self, websocket, client_id, data):
        """Обработка завершения звонка"""
        if client_id in self.active_calls:
            call_info = self.active_calls[client_id]
            duration = datetime.now() - call_info["start_time"]
            
            logger.info(f"📴 Звонок завершен: {call_info['caller_id']} (длительность: {duration})")
            
            # Отправляем прощание
            response = {
                "type": "call_ended",
                "text": "Спасибо за звонок! До свидания!",
                "duration": str(duration),
                "messages_count": len(call_info["messages"])
            }
            
            await websocket.send(json.dumps(response))
            del self.active_calls[client_id]

    async def process_with_ai(self, text, caller_id):
        """Обработка текста через TinyLlama"""
        try:
            # Формируем промпт для автоответчика
            prompt = f"""Ты - профессиональный телефонный автоответчик. 
Говори кратко, вежливо, по делу. Максимум 1-2 предложения.

Звонящий сказал: "{text}"

Твой ответ:"""

            logger.info(f"🤖 Обрабатываем через AI: {text[:50]}...")
            
            # Запускаем TinyLlama
            result = subprocess.run([
                self.ollama_path, 'run', self.model, prompt
            ], capture_output=True, text=True, timeout=15, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                response = result.stdout.strip()
                
                # Очищаем и ограничиваем ответ
                response = response.replace(prompt, "").strip()
                if len(response) > 150:
                    response = response[:150] + "..."
                
                # Убираем лишние переносы строк
                response = " ".join(response.split())
                
                logger.info(f"✅ AI ответ: {response}")
                return response if response else "Спасибо за обращение!"
            else:
                logger.error(f"❌ Ollama error: {result.stderr}")
                return "Извините, не понял вас. Можете повторить?"
                
        except subprocess.TimeoutExpired:
            logger.warning("⏰ AI timeout")
            return "Извините за задержку. Чем могу помочь?"
        except Exception as e:
            logger.error(f"❌ AI error: {e}")
            return "Извините, произошла ошибка. Попробуйте еще раз."

    async def send_error(self, websocket, error_message):
        """Отправка ошибки клиенту"""
        response = {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        try:
            await websocket.send(json.dumps(response))
        except:
            pass

    def get_stats(self):
        """Статистика активных звонков"""
        return {
            "active_calls": len(self.active_calls),
            "calls": list(self.active_calls.keys())
        }

async def main():
    autoresponder = PhoneAutoresponder()
    
    logger.info("🚀 Запускаем телефонный автоответчик...")
    logger.info("📞 WebSocket сервер: ws://localhost:8765")
    logger.info("🤖 AI модель: TinyLlama")
    
    async with websockets.serve(autoresponder.handle_client, "localhost", 8765):
        logger.info("✅ Сервер запущен! Ждем звонки...")
        await asyncio.Future()  # Работает бесконечно

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Сервер остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
