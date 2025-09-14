from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json

app = FastAPI(title="AI Autoresponder", version="1.0.0")

class ChatMessage(BaseModel):
    message: str
    caller_id: str = "unknown"

class ChatResponse(BaseModel):
    response: str
    caller_id: str

# Проверяем доступность Ollama
def check_ollama():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except:
        return False

@app.get("/")
def health_check():
    ollama_status = "online" if check_ollama() else "offline"
    return {
        "status": "AI Autoresponder Running",
        "ollama": ollama_status,
        "model": "tinyllama"
    }

@app.post("/chat", response_model=ChatResponse)
def chat_with_ai(chat: ChatMessage):
    try:
        # Формируем промпт для автоответчика
        prompt = f"""Ты - вежливый автоответчик. Отвечай кратко (максимум 2 предложения).
        
Звонящий: {chat.message}
Ответ:"""

        # Отправляем запрос к TinyLlama
        response = requests.post("http://localhost:11434/api/generate", 
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 100
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            ai_response = response.json().get("response", "Извините, не понял вас")
            
            # Ограничиваем длину ответа
            if len(ai_response) > 200:
                ai_response = ai_response[:200] + "..."
            
            return ChatResponse(
                response=ai_response.strip(),
                caller_id=chat.caller_id
            )
        else:
            raise HTTPException(status_code=500, detail="AI service unavailable")
            
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=408, detail="AI response timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/phone-call")
def handle_phone_call(chat: ChatMessage):
    """Специальный endpoint для телефонных звонков"""
    try:
        # Специальный промпт для телефонии
        prompt = f"""Ты - профессиональный телефонный автоответчик. 
Говори как секретарь: вежливо, по делу, кратко.

Звонящий сказал: "{chat.message}"

Твой ответ (максимум 1-2 предложения):"""

        response = requests.post("http://localhost:11434/api/generate", 
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,  # Менее креативно
                    "max_tokens": 50     # Короче
                }
            },
            timeout=15
        )
        
        if response.status_code == 200:
            ai_response = response.json().get("response", "Спасибо за звонок!")
            
            # Убираем лишнее и ограничиваем
            ai_response = ai_response.strip()
            if len(ai_response) > 100:
                ai_response = ai_response[:100] + "."
            
            return {
                "response": ai_response,
                "caller_id": chat.caller_id,
                "type": "phone_response"
            }
        else:
            return {
                "response": "Спасибо за звонок! Перезвоните позже.",
                "caller_id": chat.caller_id,
                "type": "fallback"
            }
            
    except Exception as e:
        return {
            "response": "Спасибо за звонок! До свидания.",
            "caller_id": chat.caller_id,
            "type": "error"
        }

if __name__ == "__main__":
    import uvicorn
    print("🤖 Запускаем AI автоответчик...")
    print("📱 API доступно на: http://localhost:8000")
    print("📋 Документация: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
