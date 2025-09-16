# 🧠📞 HR-Психоаналитик (минимальный RU)

Минимальная версия: чат‑психоанализ на русском через OpenAI GPT. Голос/HR/БД отключены.

## 🚀 Локальный запуск

```bash
pip install -r requirements.txt
python bot_minimal.py
```

## ☁️ Деплой

- `Procfile`: `worker: python bot_minimal.py`
- `railway.json` → `startCommand: python bot_minimal.py`

Переменные окружения:
- `BOT_TOKEN`
- `OPENAI_API_KEY`

## Использование
- Напишите боту сообщение — получите краткий экспресс‑анализ и рекомендации.
- Команды: `/start`, `/help`, `/cancel`. 