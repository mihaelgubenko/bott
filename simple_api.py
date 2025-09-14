#!/usr/bin/env python3
"""
Простой и быстрый API для автоответчика
"""
from fastapi import FastAPI
import requests
import subprocess
import time

app = FastAPI()

@app.get("/")
def root():
    return {"status": "AI Autoresponder", "model": "tinyllama"}

@app.get("/test")
def test_ollama():
    """Быстрый тест TinyLlama"""
    try:
        # Прямой вызов через командную строку (быстрее)
        result = subprocess.run([
            r'C:\Users\mihae\AppData\Local\Programs\Ollama\ollama.exe',
            'run', 'tinyllama', 'Привет'
        ], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:
            response = result.stdout.strip()
            # Ограничиваем ответ
            if len(response) > 100:
                response = response[:100] + "..."
            return {"response": response, "status": "ok"}
        else:
            return {"error": "Ollama error", "status": "error"}
            
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "status": "timeout"}
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.post("/chat")
def simple_chat(data: dict):
    """Простой чат"""
    message = data.get("message", "")
    
    if not message:
        return {"response": "Что вы хотели сказать?"}
    
    try:
        # Простой промпт для автоответчика
        prompt = f"Ответь кратко: {message}"
        
        result = subprocess.run([
            r'C:\Users\mihae\AppData\Local\Programs\Ollama\ollama.exe',
            'run', 'tinyllama', prompt
        ], capture_output=True, text=True, timeout=15, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:
            response = result.stdout.strip()
            # Берем только первое предложение
            response = response.split('.')[0] + '.'
            if len(response) > 150:
                response = response[:150] + "..."
            return {"response": response}
        else:
            return {"response": "Спасибо за обращение!"}
            
    except:
        return {"response": "Извините, попробуйте еще раз."}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Запускаем простой API...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
