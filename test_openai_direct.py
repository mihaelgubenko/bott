#!/usr/bin/env python3
"""
🧪 Прямое тестирование OpenAI API с вашими токенами
"""
import os
import requests
import json
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

def test_openai_chat():
    """Тестирование OpenAI Chat API"""
    print("🧪 Тестирование OpenAI API с вашими токенами...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден в .env")
        return False
        
    if not api_key.startswith('sk-'):
        print(f"❌ OpenAI ключ некорректный: {api_key[:10]}... (должен начинаться с 'sk-')")
        return False
        
    print(f"✅ OpenAI ключ найден: {api_key[:15]}...{api_key[-10:]}")
    
    # Тестируем HR консультацию
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": """Ты профессиональный HR-консультант и психоаналитик Анна.

КОНТЕКСТ: Пользователь отправил голосовое сообщение в Telegram боте для HR-психоанализа.

ЗАДАЧА: Дай профессиональную консультацию по карьере и выбору профессии.

СТИЛЬ ОТВЕТА:
- Дружелюбный но профессиональный тон
- 2-3 предложения максимум
- Конкретные рекомендации
- При необходимости направляй на полный тест"""
            },
            {
                "role": "user",
                "content": "Я работаю бухгалтером уже 5 лет, но хочу сменить профессию на что-то более творческое. Что посоветуешь?"
            }
        ],
        "max_tokens": 200,
        "temperature": 0.7
    }
    
    try:
        print("📡 Отправляем запрос к OpenAI...")
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"📊 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            ai_text = result['choices'][0]['message']['content'].strip()
            
            print("✅ SUCCESS! OpenAI API работает!")
            print("🤖 AI ответ:")
            print("-" * 50)
            print(ai_text)
            print("-" * 50)
            
            # Проверяем качество ответа
            if len(ai_text) > 20 and any(word in ai_text.lower() for word in ['творческ', 'профессия', 'карьер', 'рекоменд']):
                print("✅ Качество ответа: ОТЛИЧНОЕ (релевантно HR тематике)")
            else:
                print("⚠️ Качество ответа: СРЕДНЕЕ (не очень релевантно)")
            
            return True
            
        elif response.status_code == 401:
            print("❌ ОШИБКА 401: Неверный API ключ")
            try:
                error_info = response.json()
                print(f"   Детали: {error_info.get('error', {}).get('message', 'Неизвестная ошибка')}")
            except:
                pass
                
        elif response.status_code == 429:
            print("❌ ОШИБКА 429: Превышен лимит запросов")
            print("   Возможные причины:")
            print("   - Исчерпан баланс токенов")
            print("   - Превышен rate limit")
            print("   - Проверьте https://platform.openai.com/usage")
            
        elif response.status_code == 403:
            print("❌ ОШИБКА 403: Доступ запрещен")
            print("   Возможно, аккаунт заблокирован или нет доступа к API")
            
        else:
            print(f"❌ ОШИБКА {response.status_code}:")
            try:
                error_info = response.json()
                print(f"   {error_info}")
            except:
                print(f"   {response.text}")
                
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: Запрос превысил 30 секунд")
        
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR: Нет подключения к интернету")
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
    
    return False

def test_token_usage():
    """Проверка использования токенов"""
    print("\n💰 Проверка использования токенов...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Попробуем получить информацию об аккаунте
        response = requests.get(
            'https://api.openai.com/v1/models',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models = response.json()
            available_models = [m['id'] for m in models.get('data', []) if 'gpt' in m['id']]
            print(f"✅ Доступные GPT модели: {available_models[:3]}...")
            return True
        else:
            print("⚠️ Не удалось получить список моделей")
            
    except Exception as e:
        print(f"⚠️ Ошибка проверки: {e}")
    
    return False

def main():
    """Основная функция"""
    print("🚀 ТЕСТИРОВАНИЕ OPENAI API С ВАШИМИ ТОКЕНАМИ\n")
    
    # Основной тест
    openai_works = test_openai_chat()
    
    # Дополнительные проверки
    if openai_works:
        test_token_usage()
    
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТ:")
    print("="*60)
    
    if openai_works:
        print("🎉 SUCCESS! OpenAI API готов к работе")
        print("🤖 Ваш HR-бот будет использовать качественный AI")
        print("💡 Рекомендация: используйте OpenAI как основной AI в Railway")
        
        print("\n🚀 Следующие шаги:")
        print("1. Убедитесь что переменные настроены в Railway")
        print("2. Система автоматически будет использовать OpenAI в облаке")
        print("3. Голосовые сообщения получат качественные ответы")
        
    else:
        print("❌ ПРОБЛЕМА: OpenAI API не работает")
        print("🔧 Что проверить:")
        print("1. Правильность API ключа в .env")
        print("2. Баланс токенов на platform.openai.com/usage")
        print("3. Интернет соединение")
        print("4. Система будет использовать локальный AI как fallback")
    
    return 0 if openai_works else 1

if __name__ == "__main__":
    exit(main())
