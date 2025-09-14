#!/usr/bin/env python3
"""
Тест автоответчика с TinyLlama
"""
import requests
import time
import json

API_URL = "http://localhost:8000"

def test_api_health():
    """Проверяем работу API"""
    try:
        response = requests.get(f"{API_URL}/")
        print("🏥 Статус API:", response.json())
        return response.status_code == 200
    except Exception as e:
        print(f"❌ API недоступно: {e}")
        return False

def test_chat(message, caller_id="test"):
    """Тестируем чат"""
    try:
        data = {
            "message": message,
            "caller_id": caller_id
        }
        
        print(f"\n👤 Пользователь: {message}")
        print("🤖 AI думает...")
        
        response = requests.post(f"{API_URL}/chat", json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"🤖 AI ответ: {result['response']}")
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка теста: {e}")
        return False

def test_phone_call(message, caller_id="+1234567890"):
    """Тестируем телефонный звонок"""
    try:
        data = {
            "message": message,
            "caller_id": caller_id
        }
        
        print(f"\n📞 Звонок от {caller_id}: {message}")
        print("🤖 Автоответчик думает...")
        
        response = requests.post(f"{API_URL}/phone-call", json=data, timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            print(f"🤖 Автоответчик: {result['response']}")
            print(f"📊 Тип ответа: {result['type']}")
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка теста: {e}")
        return False

def main():
    print("🚀 Тестируем AI автоответчик с TinyLlama...")
    print("=" * 50)
    
    # Проверяем API
    if not test_api_health():
        print("❌ API не работает. Убедитесь что:")
        print("1. Ollama запущен (ollama serve)")
        print("2. TinyLlama загружен")
        print("3. AI сервер запущен (python ai_responder.py)")
        return
    
    print("\n✅ API работает!")
    
    # Тестируем чат
    print("\n📱 ТЕСТ ЧАТА:")
    test_chat("Привет! Как дела?")
    test_chat("Расскажи про свою компанию")
    test_chat("Сколько стоят ваши услуги?")
    
    # Тестируем телефонию
    print("\n📞 ТЕСТ ТЕЛЕФОННЫХ ЗВОНКОВ:")
    test_phone_call("Алло, это компания работает?")
    test_phone_call("Можно поговорить с директором?")
    test_phone_call("Какой у вас режим работы?")
    test_phone_call("Спасибо, до свидания!")
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")
    print("🌐 Документация API: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
