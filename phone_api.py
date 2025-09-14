#!/usr/bin/env python3
"""
API сервер для обработки телефонных звонков через Twilio
Интегрируется с HR-психоаналитиком
"""
import asyncio
import logging
import os
import json
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
import uvicorn
from pydantic import BaseModel
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HR-Психоаналитик Phone API", version="1.0")

# Модели данных
class CallRequest(BaseModel):
    From: str
    To: str
    CallSid: str
    Body: str = ""

class SMSRequest(BaseModel):
    From: str
    Body: str
    MessageSid: str

# Хранилище активных звонков
active_calls = {}

@app.get("/")
async def root():
    """Главная страница API"""
    return {
        "service": "HR-Психоаналитик Phone API",
        "status": "running",
        "features": [
            "Обработка входящих звонков",
            "SMS уведомления", 
            "Интеграция с психоанализом",
            "TwiML ответы"
        ],
        "endpoints": {
            "POST /webhook/call": "Обработка входящих звонков",
            "POST /webhook/sms": "Обработка SMS",
            "GET /status": "Статус звонков"
        }
    }

@app.post("/webhook/call")
async def handle_incoming_call(request: Request):
    """Обработка входящих телефонных звонков от Twilio"""
    try:
        # Получаем данные от Twilio
        form_data = await request.form()
        caller_number = form_data.get("From", "Unknown")
        call_sid = form_data.get("CallSid", "")
        
        logger.info(f"📞 Входящий звонок от {caller_number} (CallSid: {call_sid})")
        
        # Сохраняем информацию о звонке
        active_calls[call_sid] = {
            "from": caller_number,
            "start_time": datetime.now(),
            "status": "active"
        }
        
        # Генерируем TwiML ответ для автоответчика
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="ru-RU">
        Добро пожаловать в HR консультационный центр! 
        Меня зовут Анна, я ваш AI консультант по карьере и психологическому анализу.
        Как дела? Чем могу помочь с выбором профессии?
    </Say>
    <Gather action="/webhook/gather" method="POST" input="speech" speechTimeout="3" timeout="10">
        <Say voice="alice" language="ru-RU">
            Расскажите о ваших карьерных целях или задайте вопрос о профессиях.
        </Say>
    </Gather>
    <Say voice="alice" language="ru-RU">
        Извините, я вас не расслышала. До свидания!
    </Say>
    <Hangup/>
</Response>"""
        
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Ошибка обработки звонка: {e}")
        # Базовый TwiML в случае ошибки
        error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="ru-RU">
        Извините, произошла техническая ошибка. Попробуйте позвонить позже.
    </Say>
    <Hangup/>
</Response>"""
        return Response(content=error_twiml, media_type="application/xml")

@app.post("/webhook/gather")
async def handle_speech_input(request: Request):
    """Обработка голосового ввода от пользователя"""
    try:
        form_data = await request.form()
        speech_result = form_data.get("SpeechResult", "")
        call_sid = form_data.get("CallSid", "")
        caller = form_data.get("From", "Unknown")
        
        logger.info(f"🎤 Речь от {caller}: '{speech_result}'")
        
        # Получаем AI ответ на основе речи
        ai_response = await generate_ai_response(speech_result, caller)
        
        # Обновляем статус звонка
        if call_sid in active_calls:
            active_calls[call_sid]["last_speech"] = speech_result
            active_calls[call_sid]["ai_response"] = ai_response
        
        # Генерируем TwiML с AI ответом
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="ru-RU">
        {ai_response}
    </Say>
    <Gather action="/webhook/gather" method="POST" input="speech" speechTimeout="3" timeout="8">
        <Say voice="alice" language="ru-RU">
            Есть ли еще вопросы по карьере или профессиям?
        </Say>
    </Gather>
    <Say voice="alice" language="ru-RU">
        Спасибо за обращение! Для подробного анализа личности напишите нашему боту в Telegram. До свидания!
    </Say>
    <Hangup/>
</Response>"""
        
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Ошибка обработки речи: {e}")
        error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="ru-RU">
        Простите, не могу обработать ваш вопрос. До свидания!
    </Say>
    <Hangup/>
</Response>"""
        return Response(content=error_twiml, media_type="application/xml")

@app.post("/webhook/sms")
async def handle_sms(request: Request):
    """Обработка входящих SMS"""
    try:
        form_data = await request.form()
        sms_body = form_data.get("Body", "")
        sender = form_data.get("From", "Unknown")
        
        logger.info(f"📱 SMS от {sender}: '{sms_body}'")
        
        # Получаем AI ответ
        ai_response = await generate_ai_response(sms_body, sender)
        
        # TwiML ответ для SMS
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{ai_response}</Message>
</Response>"""
        
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Ошибка обработки SMS: {e}")
        return Response(content="Ошибка обработки сообщения", media_type="text/plain")

async def generate_ai_response(user_input: str, caller_id: str) -> str:
    """Генерация AI ответа на основе пользовательского ввода"""
    try:
        input_lower = user_input.lower()
        
        # HR-специфичные ответы
        if any(word in input_lower for word in ['профессия', 'работа', 'карьера', 'специальность']):
            return "Отличный вопрос о карьере! Для точных рекомендаций по профессиям мне нужно больше узнать о вас. Какая сфера вас больше всего привлекает: IT, маркетинг, медицина или что-то другое?"
            
        elif any(word in input_lower for word in ['it', 'программирование', 'компьютеры', 'айти']):
            return "IT-сфера очень перспективна! Есть много направлений: разработка, тестирование, аналитика, дизайн. Что вам ближе - создавать программы, анализировать данные или работать с интерфейсами?"
            
        elif any(word in input_lower for word in ['маркетинг', 'реклама', 'продажи']):
            return "Маркетинг требует креативности и коммуникативных навыков. Вас больше интересует стратегия, креатив, аналитика или прямые продажи? Расскажите о своих сильных сторонах."
            
        elif any(word in input_lower for word in ['психология', 'анализ', 'тест', 'личность']):
            return "Психологический анализ - моя специализация! Я использую методики Фрейда, Юнга и современные тесты. Для полного анализа рекомендую наш Telegram-бот, где можно пройти детальное тестирование."
            
        elif any(word in input_lower for word in ['учиться', 'образование', 'курсы']):
            return "Образование - ключ к успеху! Важно выбрать направление, которое соответствует вашему типу личности. Какие предметы давались вам легче всего в школе или университете?"
            
        elif any(word in input_lower for word in ['зарплата', 'деньги', 'доход']):
            return "Финансовая мотивация важна, но не единственная. Высокие доходы обычно в IT, финансах, медицине, консалтинге. Но главное - найти дело по душе. Что вас действительно увлекает?"
            
        elif any(word in input_lower for word in ['сменить', 'поменять', 'новая']):
            return "Смена профессии в любом возрасте возможна! Важно понять, что именно не устраивает сейчас и к чему стремитесь. Расскажите, что бы вы хотели изменить в своей карьере?"
            
        elif any(word in input_lower for word in ['помощь', 'совет', 'не знаю']):
            return "Конечно помогу! Выбор профессии - важное решение. Давайте начнем с простого: что вам нравится делать в свободное время? Какие задачи даются легко?"
            
        elif any(word in input_lower for word in ['привет', 'здравствуйте', 'добрый']):
            return "Добро пожаловать! Меня зовут Анна, я AI-консультант по карьере. Помогаю людям найти подходящую профессию на основе психологического анализа. С чего начнем?"
            
        elif any(word in input_lower for word in ['спасибо', 'благодарю']):
            return "Пожалуйста! Рада была помочь. Для более глубокого анализа личности и детальных рекомендаций попробуйте наш Telegram-бот. Удачи в карьере!"
            
        else:
            return f"Интересно! Понимаю, что карьерные вопросы сложные. Чтобы дать точные рекомендации, расскажите: какая сфера деятельности вас больше всего привлекает или беспокоит?"
            
    except Exception as e:
        logger.error(f"Ошибка генерации AI ответа: {e}")
        return "Извините, возникла техническая проблема. Попробуйте переформулировать вопрос или обратитесь к нашему боту в Telegram."

@app.get("/status")
async def get_call_status():
    """Получение статуса активных звонков"""
    return {
        "active_calls": len(active_calls),
        "calls": [
            {
                "call_sid": call_id,
                "from": call_info["from"],
                "duration": str(datetime.now() - call_info["start_time"]),
                "status": call_info["status"]
            }
            for call_id, call_info in active_calls.items()
        ]
    }

@app.post("/test/call")
async def test_call_endpoint(request: CallRequest):
    """Тестовый endpoint для проверки без Twilio"""
    response = await generate_ai_response(request.Body, request.From)
    return {
        "caller": request.From,
        "input": request.Body,
        "ai_response": response,
        "status": "test_ok"
    }

if __name__ == "__main__":
    print("🚀 Запуск Phone API сервера для HR-Психоаналитика...")
    print("📞 Endpoints:")
    print("  POST /webhook/call - Входящие звонки")
    print("  POST /webhook/sms - SMS сообщения") 
    print("  GET /status - Статус звонков")
    print("  POST /test/call - Тестирование")
    
    # Запуск сервера
    uvicorn.run(
        "phone_api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )
