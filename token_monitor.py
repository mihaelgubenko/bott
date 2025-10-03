"""
Модуль для мониторинга и управления токенами в MindScanBot
Предотвращает обрыв диалогов из-за превышения лимитов токенов
"""

import logging
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    """Информация об использовании токенов"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float

class TokenMonitor:
    """Монитор токенов для предотвращения обрыва диалогов"""
    
    def __init__(self):
        # Примерные лимиты токенов для разных моделей
        self.model_limits = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-3.5-turbo": 4096
        }
        
        # Примерные цены за токен (в долларах)
        self.token_costs = {
            "gpt-4": {"input": 0.00003, "output": 0.00006},
            "gpt-4-turbo": {"input": 0.00001, "output": 0.00003},
            "gpt-3.5-turbo": {"input": 0.0000015, "output": 0.000002}
        }
    
    def estimate_tokens(self, text: str) -> int:
        """Примерная оценка количества токенов в тексте"""
        # Простая оценка: 1 токен ≈ 4 символа для русского текста
        return len(text) // 4
    
    def check_prompt_size(self, prompt: str, model: str = "gpt-4") -> Tuple[bool, int]:
        """Проверка размера промпта"""
        estimated_tokens = self.estimate_tokens(prompt)
        max_tokens = self.model_limits.get(model, 8192)
        
        # Оставляем место для ответа (примерно 20% от лимита)
        safe_limit = int(max_tokens * 0.8)
        
        is_safe = estimated_tokens < safe_limit
        return is_safe, estimated_tokens
    
    def optimize_prompt(self, prompt: str, max_tokens: int = 6000) -> str:
        """Оптимизация промпта для уменьшения количества токенов"""
        current_tokens = self.estimate_tokens(prompt)
        
        if current_tokens <= max_tokens:
            return prompt
        
        # Сокращаем промпт
        target_length = max_tokens * 4  # 4 символа на токен
        if len(prompt) <= target_length:
            return prompt
        
        # Находим важные части промпта
        important_parts = []
        
        # Ищем инструкции (строки с заглавными буквами)
        instructions = re.findall(r'[А-Я][А-Я\s]+:', prompt)
        for instruction in instructions:
            start = prompt.find(instruction)
            end = prompt.find('\n', start)
            if end == -1:
                end = len(prompt)
            important_parts.append(prompt[start:end])
        
        # Ищем контекст разговора
        context_match = re.search(r'КОНТЕКСТ РАЗГОВОРА:.*?(?=\n\n|\n[А-Я]|$)', prompt, re.DOTALL)
        if context_match:
            context = context_match.group(0)
            # Сокращаем контекст
            if len(context) > target_length // 2:
                context = context[:target_length // 2] + "..."
            important_parts.append(context)
        
        # Собираем оптимизированный промпт
        optimized = '\n\n'.join(important_parts)
        
        # Если все еще слишком длинный, обрезаем
        if len(optimized) > target_length:
            optimized = optimized[:target_length] + "..."
        
        return optimized
    
    def calculate_usage(self, prompt: str, response: str, model: str = "gpt-4") -> TokenUsage:
        """Расчет использования токенов"""
        prompt_tokens = self.estimate_tokens(prompt)
        completion_tokens = self.estimate_tokens(response)
        total_tokens = prompt_tokens + completion_tokens
        
        costs = self.token_costs.get(model, self.token_costs["gpt-4"])
        estimated_cost = (prompt_tokens * costs["input"] + 
                         completion_tokens * costs["output"])
        
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost
        )
    
    def should_split_response(self, response: str) -> bool:
        """Определяет, нужно ли разбивать ответ на части"""
        # Если ответ больше 4000 символов, разбиваем
        return len(response) > 4000
    
    def split_response_smart(self, response: str, max_length: int = 4000) -> List[str]:
        """Умное разбиение ответа на части"""
        if len(response) <= max_length:
            return [response]
        
        # Разбиваем по предложениям
        sentences = response.split('. ')
        parts = []
        current_part = ""
        
        for sentence in sentences:
            if len(current_part + sentence + '. ') <= max_length:
                current_part += sentence + '. '
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = sentence + '. '
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def log_usage(self, usage: TokenUsage, user_id: int, prompt_type: str):
        """Логирование использования токенов"""
        logger.info(
            f"Token usage for user {user_id} ({prompt_type}): "
            f"{usage.total_tokens} tokens, ${usage.estimated_cost:.4f}"
        )

# Глобальный экземпляр монитора
token_monitor = TokenMonitor()

def get_token_monitor() -> TokenMonitor:
    """Получить экземпляр монитора токенов"""
    return token_monitor

# Пример использования
if __name__ == "__main__":
    monitor = get_token_monitor()
    
    test_prompt = "Ты — профессиональный HR-психоаналитик..."
    test_response = "Анализ показывает..."
    
    # Проверка размера промпта
    is_safe, tokens = monitor.check_prompt_size(test_prompt)
    print(f"Промпт безопасен: {is_safe}, токенов: {tokens}")
    
    # Расчет использования
    usage = monitor.calculate_usage(test_prompt, test_response)
    print(f"Использовано токенов: {usage.total_tokens}")
    print(f"Примерная стоимость: ${usage.estimated_cost:.4f}")