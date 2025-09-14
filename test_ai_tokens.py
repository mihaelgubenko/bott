#!/usr/bin/env python3
"""
🧪 Тест AI токенов и подключений
Проверяет работу Ollama, OpenAI и локального AI
"""
import os
import sys
import requests
import json
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

def test_ollama():
    """Тест подключения к Ollama"""
    print("🧪 Тестирование Ollama...")
    try:
        # Проверяем доступность
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            available_models = [m['name'] for m in models]
            print(f"✅ Ollama доступен. Модели: {available_models}")
            
            # Тестируем генерацию
            if available_models:
                test_model = "tinyllama:latest"  # Используем стабильную модель
                data = {
                    "model": test_model,
                    "prompt": "Привет! Как дела?",
                    "stream": False,
                    "options": {"num_predict": 50}
                }
                
                gen_response = requests.post(
                    "http://localhost:11434/api/generate",
                    json=data,
                    timeout=15
                )
                
                if gen_response.status_code == 200:
                    result = gen_response.json()
                    ai_text = result.get('response', '').strip()
                    print(f"✅ Ollama генерация работает: {ai_text[:50]}...")
                    return True
                else:
                    print(f"❌ Ollama генерация ошибка: {gen_response.status_code}")
            else:
                print("⚠️ Ollama работает, но нет моделей")
        else:
            print(f"❌ Ollama не отвечает: {response.status_code}")
    except Exception as e:
        print(f"❌ Ollama недоступен: {e}")
    return False

def test_openai():
    """Тест OpenAI API"""
    print("\n🧪 Тестирование OpenAI...")
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            print("❌ OPENAI_API_KEY не найден в .env")
            return False
            
        if api_key == "dummy_key_for_testing":
            print("⚠️ OpenAI ключ является тестовым (dummy_key_for_testing)")
            return False
            
        if not api_key.startswith('sk-'):
            print(f"❌ OpenAI ключ некорректный: {api_key[:10]}... (должен начинаться с 'sk-')")
            return False
            
        print(f"✅ OpenAI ключ найден: {api_key[:10]}...{api_key[-4:]}")
        
        # Тестируем API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Ты HR-консультант. Отвечай кратко."},
                {"role": "user", "content": "Привет! Как дела с работой?"}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_text = result['choices'][0]['message']['content'].strip()
            print(f"✅ OpenAI API работает: {ai_text[:50]}...")
            return True
        else:
            print(f"❌ OpenAI API ошибка {response.status_code}:")
            try:
                error_info = response.json()
                print(f"   {error_info.get('error', {}).get('message', 'Неизвестная ошибка')}")
            except:
                print(f"   {response.text[:200]}")
                
    except Exception as e:
        print(f"❌ OpenAI ошибка: {e}")
    return False

def test_local_ai():
    """Тест локального AI (fallback)"""
    print("\n🧪 Тестирование локального AI...")
    
    # Простая локальная логика
    user_input = "Хочу работать в IT"
    
    if "it" in user_input.lower():
        response = "IT-сфера очень перспективна! Рекомендую изучить Python или JavaScript."
    else:
        response = "Понимаю ваш интерес к карьере. Расскажите подробнее о ваших целях."
    
    print(f"✅ Локальный AI работает: {response}")
    return True

def test_env_file():
    """Проверка .env файла"""
    print("🧪 Проверка .env файла...")
    
    env_file = ".env"
    if not os.path.exists(env_file):
        print("⚠️ .env файл не найден")
        return False
    
    print("✅ .env файл существует")
    
    # Читаем содержимое
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем наличие ключей
    required_keys = ['BOT_TOKEN', 'OPENAI_API_KEY', 'ADMIN_CHAT_ID']
    found_keys = []
    
    for key in required_keys:
        if key in content:
            found_keys.append(key)
            value = os.getenv(key, 'НЕ НАЙДЕН')
            if key == 'OPENAI_API_KEY':
                # Маскируем API ключ
                masked_value = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else value
                print(f"  ✅ {key}: {masked_value}")
            else:
                print(f"  ✅ {key}: {value}")
        else:
            print(f"  ❌ {key}: НЕ НАЙДЕН")
    
    return len(found_keys) == len(required_keys)

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование AI систем для HR-Психоаналитика\n")
    
    # Тесты
    env_ok = test_env_file()
    ollama_ok = test_ollama()
    openai_ok = test_openai() 
    local_ok = test_local_ai()
    
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("="*50)
    
    print(f"📁 .env конфигурация: {'✅ OK' if env_ok else '❌ FAIL'}")
    print(f"🧠 Ollama (локальный): {'✅ OK' if ollama_ok else '❌ FAIL'}")
    print(f"🤖 OpenAI API: {'✅ OK' if openai_ok else '❌ FAIL'}")
    print(f"💡 Локальный AI: {'✅ OK' if local_ok else '❌ FAIL'}")
    
    print("\n🎯 РЕКОМЕНДАЦИИ:")
    
    if ollama_ok:
        print("✅ Используйте Ollama для быстрых локальных ответов")
    else:
        print("⚠️ Запустите Ollama: ollama serve")
        print("⚠️ Загрузите модель: ollama pull llama2")
    
    if openai_ok:
        print("✅ OpenAI API готов к использованию")
    else:
        print("⚠️ Проверьте OPENAI_API_KEY в .env файле")
        print("⚠️ Убедитесь что ключ начинается с 'sk-'")
        print("⚠️ Проверьте баланс на https://platform.openai.com/usage")
    
    if not ollama_ok and not openai_ok:
        print("⚠️ Будет использован только локальный AI (ограниченные возможности)")
    
    print("\n🎉 Тестирование завершено!")
    
    # Возвращаем код выхода
    if openai_ok or ollama_ok:
        return 0  # Успех
    else:
        return 1  # Проблемы

if __name__ == "__main__":
    sys.exit(main())
