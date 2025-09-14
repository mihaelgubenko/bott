# 🌐 Удаленный деплой телефонной системы

## 🎯 **Варианты деплоя:**

### 1️⃣ **Railway (рекомендуется)**
- ✅ Бесплатный план: 500 часов/месяц
- ✅ Автодеплой из GitHub
- ✅ HTTPS автоматически
- ✅ WebSocket поддержка

### 2️⃣ **Heroku**
- ✅ Бесплатные dyno часы
- ✅ Easy setup
- ❌ Нужна настройка WebSocket

### 3️⃣ **VPS (DigitalOcean, Vultr)**
- ✅ Полный контроль
- ✅ Дешево ($5/месяц)
- ❌ Нужна настройка

---

## 🚀 **Railway деплой (быстрый)**

### **Шаг 1: Подготовка**
```bash
# Коммитим изменения
git add free_phone_server.py remote_phone.html Procfile REMOTE_DEPLOY.md
git commit -m "🌐 Добавлен удаленный деплой телефонной системы"
git push origin main
```

### **Шаг 2: Railway настройка**
1. Зайдите на [railway.app](https://railway.app)
2. **Connect GitHub repo** → выберите `mihaelgubenko/bott`
3. **Deploy from main branch**
4. Дождитесь успешного деплоя ✅

### **Шаг 3: Получение URL**
После деплоя Railway покажет URL типа:
```
https://bott-production-xxxx.up.railway.app
```

### **Шаг 4: Тестирование**
1. Откройте `remote_phone.html` в браузере
2. Введите URL: `wss://bott-production-xxxx.up.railway.app`
3. Нажмите **"Подключиться"**
4. Начните разговор! 🎤

---

## 🔧 **Конфигурация для продакшн**

### **Переменные окружения в Railway:**
```bash
# Если у вас есть OpenAI ключ
OPENAI_API_KEY=sk-ваш-реальный-ключ

# Для использования только Ollama (без OpenAI)
USE_OLLAMA=true

# Railway автоматически добавляет:
PORT=8080
RAILWAY_ENVIRONMENT=production
```

### **Проблема: Ollama недоступен в облаке**
Railway/Heroku не поддерживают Ollama. Решения:

**Вариант A: Только OpenAI**
```python
# В free_phone_server.py
USE_OLLAMA = False  # Принудительно использовать OpenAI
```

**Вариант B: Внешний Ollama**
```python
# Настройте OLLAMA_URL на внешний сервер
OLLAMA_URL = "https://ваш-ollama-сервер.com"
```

**Вариант C: Локальный AI (fallback)**
Система автоматически переключится на `local_ai_response()` если Ollama и OpenAI недоступны.

---

## 🎯 **Тестирование удаленной системы**

### **Тест 1: Локальное соединение**
```bash
# Запустите локально
python free_phone_server.py

# В remote_phone.html введите:
ws://localhost:8765
```

### **Тест 2: Удаленное соединение**
```bash
# В remote_phone.html введите ваш Railway URL:
wss://bott-production-xxxx.up.railway.app
```

### **Тест 3: Проверка через curl**
```bash
# Проверка что сервер отвечает
curl https://bott-production-xxxx.up.railway.app

# Тест WebSocket (если wscat установлен)
wscat -c wss://bott-production-xxxx.up.railway.app
```

---

## 🔒 **HTTPS и безопасность**

### **Почему нужен HTTPS/WSS:**
- 🎤 **Микрофон** требует HTTPS
- 🔒 **Безопасность** данных
- 🌐 **Совместимость** с браузерами

### **Автоматический HTTPS:**
Railway/Heroku автоматически дают HTTPS:
- `http://` → `https://`
- `ws://` → `wss://`

### **Кастомный домен (опционально):**
1. Купите домен (например, на Namecheap)
2. В Railway: **Settings** → **Domains** → **Custom Domain**
3. Добавьте CNAME запись: `phone.вашдомен.com` → `bott-production-xxxx.up.railway.app`

---

## 📱 **Интеграция с Telegram**

### **Добавить ссылку в бота:**
```python
# В main.py обновите phone_mode_command:
async def phone_mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_url = "https://ваш-домен.railway.app/remote_phone.html"
    
    await update.message.reply_text(
        f"📞 **Телефонная консультация**\n\n"
        f"🌐 **Откройте веб-интерфейс:**\n{phone_url}\n\n"
        f"🎤 Говорите прямо в браузере\n"
        f"🤖 AI ответит через Ollama/OpenAI\n"
        f"🔒 Работает в любом браузере",
        parse_mode=ParseMode.MARKDOWN
    )
```

---

## 📊 **Мониторинг продакшн**

### **Railway логи:**
```bash
# Установите Railway CLI
npm install -g @railway/cli

# Смотрите логи
railway logs
```

### **Статус системы:**
```bash
# Проверка работоспособности
curl https://ваш-домен.railway.app/health

# Статистика подключений  
curl https://ваш-домен.railway.app/stats
```

### **Добавить healthcheck в сервер:**
```python
# В free_phone_server.py добавьте:
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "phone_server"}

@app.get("/stats") 
async def get_stats():
    return {
        "active_connections": len(server.active_calls),
        "total_calls": server.total_calls,
        "uptime": "working"
    }
```

---

## 💰 **Стоимость деплоя**

### **Railway (бесплатно):**
- ✅ 500 часов/месяц бесплатно
- ✅ Автодеплой
- ✅ HTTPS включен
- 💰 $5/месяц за больше ресурсов

### **Heroku (бесплатно/ограниченно):**
- ✅ 550 часов/месяц бесплатно
- ❌ Засыпает через 30 минут
- 💰 $7/месяц за постоянную работу

### **VPS ($5/месяц):**
- ✅ 24/7 работа
- ✅ Полный контроль
- ❌ Нужна настройка сервера

---

## 🎉 **Готово!**

После деплоя у вас будет:

📞 **Удаленная телефонная система:**
- Доступна по ссылке из любой точки мира
- Работает в любом браузере с микрофоном
- Интегрирована с AI (OpenAI/локальный)

🤖 **Telegram бот + телефония:**
- Команда `/phone` показывает ссылку
- Психоанализ в Telegram
- Голосовые консультации в браузере

📊 **Коммерческая готовность:**
- Профессиональный интерфейс
- Логирование и мониторинг
- Масштабируемость

**Ваша система готова принимать клиентов со всего мира! 🌍**
