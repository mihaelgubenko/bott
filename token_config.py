"""
Конфигурация токенов для HR-Психоаналитического бота
Позволяет легко настраивать лимиты и параметры использования токенов
"""

# Базовые лимиты токенов для разных типов ответов
TOKEN_LIMITS = {
    "express_analysis": 400,           # Экспресс-анализ личности
    "full_analysis": 1200,            # Полный психоанализ
    "psychology_consultation": 250,    # Психологическая консультация
    "smart_response": 180,            # Умный ответ в диалоге
    "default": 200                     # Стандартный ответ
}

# Дневные лимиты токенов
DAILY_LIMITS = {
    "free_tier": 10000,               # Бесплатный уровень
    "premium_tier": 50000,            # Премиум уровень
    "admin_tier": 100000              # Админский уровень
}

# Плавающие лимиты (проценты от базового лимита при высоком использовании)
FLOATING_LIMITS = {
    "high_usage_threshold": 0.8,      # Порог высокого использования (80%)
    "medium_usage_threshold": 0.6,    # Порог среднего использования (60%)
    "high_usage_reduction": 0.7,       # Сокращение при высоком использовании (70%)
    "medium_usage_reduction": 0.85    # Сокращение при среднем использовании (85%)
}

# Настройки мониторинга
MONITORING_SETTINGS = {
    "log_token_usage": True,           # Логировать использование токенов
    "warn_at_80_percent": True,        # Предупреждать при 80% использования
    "warn_at_60_percent": True,        # Предупреждать при 60% использования
    "auto_reduce_at_high_usage": True  # Автоматически сокращать при высоком использовании
}

# Настройки оптимизации промптов
PROMPT_OPTIMIZATION = {
    "max_prompt_length": 2000,         # Максимальная длина промпта в символах
    "compress_long_prompts": True,     # Сжимать длинные промпты
    "remove_redundant_text": True,     # Удалять избыточный текст
    "use_short_instructions": True      # Использовать короткие инструкции
}

# Настройки ответов
RESPONSE_SETTINGS = {
    "max_response_length": 500,        # Максимальная длина ответа в токенах
    "prefer_short_responses": True,    # Предпочитать короткие ответы
    "use_bullet_points": True,         # Использовать маркированные списки
    "emojis_enabled": True            # Использовать эмодзи для структурирования
}

def get_token_limit(response_type: str, usage_ratio: float = 0.0) -> int:
    """
    Получить лимит токенов с учетом плавающих лимитов
    
    Args:
        response_type: Тип ответа
        usage_ratio: Текущее использование в процентах (0.0 - 1.0)
    
    Returns:
        Лимит токенов для данного типа ответа
    """
    base_limit = TOKEN_LIMITS.get(response_type, TOKEN_LIMITS["default"])
    
    if not MONITORING_SETTINGS["auto_reduce_at_high_usage"]:
        return base_limit
    
    if usage_ratio >= FLOATING_LIMITS["high_usage_threshold"]:
        return int(base_limit * FLOATING_LIMITS["high_usage_reduction"])
    elif usage_ratio >= FLOATING_LIMITS["medium_usage_threshold"]:
        return int(base_limit * FLOATING_LIMITS["medium_usage_reduction"])
    else:
        return base_limit

def should_warn_usage(usage_ratio: float) -> bool:
    """Проверить, нужно ли предупреждать о высоком использовании"""
    if usage_ratio >= FLOATING_LIMITS["high_usage_threshold"] and MONITORING_SETTINGS["warn_at_80_percent"]:
        return True
    elif usage_ratio >= FLOATING_LIMITS["medium_usage_threshold"] and MONITORING_SETTINGS["warn_at_60_percent"]:
        return True
    return False

def get_warning_message(usage_ratio: float) -> str:
    """Получить сообщение предупреждения"""
    if usage_ratio >= FLOATING_LIMITS["high_usage_threshold"]:
        return "⚠️ ВНИМАНИЕ: Использовано больше 80% дневного лимита токенов!"
    elif usage_ratio >= FLOATING_LIMITS["medium_usage_threshold"]:
        return "⚡ Уведомление: Использовано больше 60% дневного лимита токенов"
    return ""

# Пример использования
if __name__ == "__main__":
    # Тестируем функцию получения лимитов
    print("Тестирование лимитов токенов:")
    print(f"Экспресс-анализ (0% использования): {get_token_limit('express_analysis', 0.0)}")
    print(f"Экспресс-анализ (70% использования): {get_token_limit('express_analysis', 0.7)}")
    print(f"Экспресс-анализ (85% использования): {get_token_limit('express_analysis', 0.85)}")
    
    # Тестируем предупреждения
    print("\nТестирование предупреждений:")
    print(f"50% использования: {should_warn_usage(0.5)}")
    print(f"65% использования: {should_warn_usage(0.65)}")
    print(f"85% использования: {should_warn_usage(0.85)}")