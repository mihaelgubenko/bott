"""
Менеджер токенов для оптимизации использования OpenAI API
"""

import tiktoken
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    """Информация об использовании токенов"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float

class TokenManager:
    """Менеджер токенов для оптимизации запросов к OpenAI"""
    
    def __init__(self, config):
        self.config = config
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Стоимость токенов для GPT-4 (примерная)
        self.token_costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},  # за 1K токенов
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
        }
    
    def count_tokens(self, text: str) -> int:
        """Подсчет токенов в тексте"""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Ошибка подсчета токенов: {e}")
            # Примерная оценка: 1 токен ≈ 4 символа
            return len(text) // 4
    
    def count_tokens_list(self, texts: List[str]) -> int:
        """Подсчет токенов в списке текстов"""
        return sum(self.count_tokens(text) for text in texts)
    
    def estimate_response_tokens(self, prompt_tokens: int, context_length: int) -> int:
        """Оценка количества токенов в ответе"""
        # Базовая оценка на основе длины промпта и контекста
        base_estimate = min(500, prompt_tokens // 4)
        
        # Корректировка на основе контекста
        if context_length > 10:
            base_estimate = min(base_estimate + 200, 1000)
        
        return min(base_estimate, self.config.RESPONSE_TOKENS)
    
    def calculate_available_tokens(self, prompt: str, context: str, user_type: str = "free") -> int:
        """Расчет доступных токенов для ответа"""
        prompt_tokens = self.count_tokens(prompt)
        context_tokens = self.count_tokens(context)
        
        # Получаем лимиты для пользователя
        user_limits = self.config.get_user_limits(user_type)
        max_tokens = user_limits["max_tokens"]
        
        # Резервируем место для ответа
        available_for_prompt = max_tokens - self.config.RESPONSE_TOKENS
        
        # Если промпт + контекст превышают лимит
        if prompt_tokens + context_tokens > available_for_prompt:
            # Сжимаем контекст
            max_context_tokens = available_for_prompt - prompt_tokens
            return max_context_tokens
        
        return context_tokens
    
    def optimize_prompt(self, prompt: str, context: str, user_type: str = "free") -> Tuple[str, str, TokenUsage]:
        """Оптимизация промпта с учетом лимитов токенов"""
        prompt_tokens = self.count_tokens(prompt)
        context_tokens = self.count_tokens(context)
        
        # Получаем адаптивные лимиты
        conversation_length = len(context.split('\n')) if context else 0
        adaptive_limits = self.config.get_adaptive_limits(conversation_length, user_type)
        max_tokens = adaptive_limits["max_tokens"]
        
        # Резервируем место для ответа
        available_for_prompt = max_tokens - self.config.RESPONSE_TOKENS
        
        # Если все помещается
        if prompt_tokens + context_tokens <= available_for_prompt:
            total_tokens = prompt_tokens + context_tokens
            estimated_cost = self._calculate_cost(total_tokens, "gpt-4")
            
            return prompt, context, TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=self.config.RESPONSE_TOKENS,
                total_tokens=total_tokens + self.config.RESPONSE_TOKENS,
                estimated_cost=estimated_cost
            )
        
        # Нужно сжимать контекст
        max_context_tokens = available_for_prompt - prompt_tokens
        
        if max_context_tokens <= 0:
            # Если даже промпт не помещается, используем минимальный контекст
            max_context_tokens = self.config.MIN_TOKENS
            logger.warning(f"Промпт слишком длинный, используется минимальный контекст")
        
        # Сжимаем контекст
        compressed_context = self._compress_context(context, max_context_tokens)
        
        final_tokens = prompt_tokens + self.count_tokens(compressed_context)
        estimated_cost = self._calculate_cost(final_tokens, "gpt-4")
        
        return prompt, compressed_context, TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=self.config.RESPONSE_TOKENS,
            total_tokens=final_tokens + self.config.RESPONSE_TOKENS,
            estimated_cost=estimated_cost
        )
    
    def _compress_context(self, context: str, max_tokens: int) -> str:
        """Сжатие контекста с сохранением важной информации"""
        if self.count_tokens(context) <= max_tokens:
            return context
        
        # Разбиваем на предложения
        sentences = context.split('. ')
        
        # Приоритизируем последние предложения
        important_sentences = sentences[-3:]  # Последние 3 предложения
        
        # Добавляем предложения с ключевыми словами
        key_words = ['важно', 'проблема', 'цель', 'мечта', 'страх', 'тревога', 'работа', 'карьера']
        for sentence in sentences[:-3]:
            if any(word in sentence.lower() for word in key_words):
                important_sentences.insert(-3, sentence)
        
        # Собираем сжатый контекст
        compressed = '. '.join(important_sentences)
        
        # Если все еще не помещается, обрезаем
        while self.count_tokens(compressed) > max_tokens and len(compressed) > 100:
            compressed = compressed[:-100] + "..."
        
        return compressed
    
    def _calculate_cost(self, tokens: int, model: str = "gpt-4") -> float:
        """Расчет примерной стоимости запроса"""
        if model not in self.token_costs:
            model = "gpt-4"
        
        cost_per_1k = self.token_costs[model]["input"]
        return (tokens / 1000) * cost_per_1k
    
    def split_long_response(self, response: str, max_length: int = None) -> List[str]:
        """Разбиение длинного ответа на части"""
        if max_length is None:
            max_length = self.config.MAX_MESSAGE_LENGTH
        
        if len(response) <= max_length:
            return [response]
        
        parts = []
        current_part = ""
        
        # Разбиваем по абзацам
        paragraphs = response.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_part + paragraph) <= max_length:
                current_part += "\n\n" + paragraph if current_part else paragraph
            else:
                if current_part:
                    parts.append(current_part.strip())
                
                # Если один абзац слишком длинный, разбиваем его
                if len(paragraph) > max_length:
                    sub_parts = self._split_long_paragraph(paragraph, max_length)
                    parts.extend(sub_parts[:-1])  # Добавляем все кроме последнего
                    current_part = sub_parts[-1]  # Последний становится текущим
                else:
                    current_part = paragraph
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def _split_long_paragraph(self, paragraph: str, max_length: int) -> List[str]:
        """Разбиение длинного абзаца на части"""
        parts = []
        current_part = ""
        
        sentences = paragraph.split('. ')
        
        for sentence in sentences:
            if len(current_part + sentence) <= max_length:
                current_part += ". " + sentence if current_part else sentence
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = sentence
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def is_response_truncated(self, response: str) -> bool:
        """Проверка, обрезан ли ответ"""
        # Простые индикаторы обрезанного ответа
        truncation_indicators = [
            response.endswith('...'),
            response.endswith('...'),
            not response.endswith('.'),
            not response.endswith('!'),
            not response.endswith('?'),
            len(response.split()) < 10  # Слишком короткий ответ
        ]
        
        return any(truncation_indicators)
    
    def get_continuation_prompt(self, truncated_response: str) -> str:
        """Получение промпта для продолжения обрезанного ответа"""
        # Берем последние 200 символов для контекста
        context = truncated_response[-200:] if len(truncated_response) > 200 else truncated_response
        
        return f"""Продолжи ответ с того места, где остановился. 
Контекст: {context}

Продолжение:"""