"""
Компрессор контекста для умного сжатия диалогов
"""

import re
import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Структура сообщения"""
    text: str
    importance: float
    timestamp: str = ""
    user_id: int = 0

class ContextCompressor:
    """Компрессор контекста для оптимизации диалогов"""
    
    def __init__(self, config):
        self.config = config
        
        # Ключевые слова для определения важности
        self.importance_keywords = {
            'high': ['важно', 'проблема', 'цель', 'мечта', 'страх', 'тревога', 'кризис', 'срочно'],
            'medium': ['работа', 'карьера', 'отношения', 'семья', 'деньги', 'здоровье'],
            'low': ['привет', 'спасибо', 'хорошо', 'понятно', 'да', 'нет']
        }
        
        # Паттерны для извлечения ключевой информации
        self.key_patterns = [
            r'я хочу (.+)',
            r'моя цель (.+)',
            r'моя проблема (.+)',
            r'я боюсь (.+)',
            r'я мечтаю (.+)',
            r'я работаю (.+)',
            r'я изучаю (.+)',
            r'я планирую (.+)'
        ]
    
    def compress_conversation(self, messages: List[str], max_tokens: int) -> str:
        """Сжатие диалога с сохранением важной информации"""
        if not messages:
            return ""
        
        # Анализируем важность каждого сообщения
        analyzed_messages = self._analyze_messages(messages)
        
        # Если все помещается, возвращаем как есть
        total_tokens = sum(self._count_tokens(msg.text) for msg in analyzed_messages)
        if total_tokens <= max_tokens:
            return self._format_messages(analyzed_messages)
        
        # Приоритизируем сообщения
        prioritized = self._prioritize_messages(analyzed_messages)
        
        # Выбираем сообщения, которые помещаются в лимит
        selected_messages = self._select_messages(prioritized, max_tokens)
        
        # Создаем сжатый контекст
        compressed = self._create_compressed_context(selected_messages, analyzed_messages)
        
        return compressed
    
    def _analyze_messages(self, messages: List[str]) -> List[Message]:
        """Анализ важности сообщений"""
        analyzed = []
        
        for i, text in enumerate(messages):
            importance = self._calculate_importance(text, i, len(messages))
            analyzed.append(Message(
                text=text,
                importance=importance,
                timestamp=f"msg_{i+1}"
            ))
        
        return analyzed
    
    def _calculate_importance(self, text: str, position: int, total: int) -> float:
        """Расчет важности сообщения"""
        importance = 0.0
        text_lower = text.lower()
        
        # Базовый вес на основе позиции (последние сообщения важнее)
        position_weight = (position + 1) / total
        importance += position_weight * 0.3
        
        # Вес на основе ключевых слов
        for level, keywords in self.importance_keywords.items():
            weight = {'high': 0.5, 'medium': 0.3, 'low': 0.1}[level]
            keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
            importance += keyword_count * weight
        
        # Вес на основе длины (более длинные сообщения обычно важнее)
        length_weight = min(len(text) / 200, 1.0) * 0.2
        importance += length_weight
        
        # Вес на основе паттернов
        pattern_weight = self._check_key_patterns(text_lower) * 0.3
        importance += pattern_weight
        
        return min(importance, 1.0)
    
    def _check_key_patterns(self, text: str) -> float:
        """Проверка ключевых паттернов в тексте"""
        pattern_matches = 0
        for pattern in self.key_patterns:
            if re.search(pattern, text):
                pattern_matches += 1
        
        return min(pattern_matches / len(self.key_patterns), 1.0)
    
    def _prioritize_messages(self, messages: List[Message]) -> List[Message]:
        """Приоритизация сообщений по важности"""
        # Сортируем по важности (убывание)
        return sorted(messages, key=lambda x: x.importance, reverse=True)
    
    def _select_messages(self, prioritized: List[Message], max_tokens: int) -> List[Message]:
        """Выбор сообщений, которые помещаются в лимит токенов"""
        selected = []
        current_tokens = 0
        
        for message in prioritized:
            message_tokens = self._count_tokens(message.text)
            
            if current_tokens + message_tokens <= max_tokens:
                selected.append(message)
                current_tokens += message_tokens
            else:
                # Если не помещается полностью, берем часть
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 50:  # Минимум 50 токенов для частичного сообщения
                    partial_text = self._truncate_text(message.text, remaining_tokens)
                    selected.append(Message(
                        text=partial_text + "...",
                        importance=message.importance,
                        timestamp=message.timestamp
                    ))
                break
        
        return selected
    
    def _create_compressed_context(self, selected: List[Message], all_messages: List[Message]) -> str:
        """Создание сжатого контекста"""
        if not selected:
            return "Контекст недоступен"
        
        # Если выбраны не все сообщения, добавляем префикс
        if len(selected) < len(all_messages):
            context_parts = [
                f"[Сжатый контекст из {len(all_messages)} сообщений]",
                ""
            ]
        else:
            context_parts = []
        
        # Добавляем выбранные сообщения
        for message in selected:
            context_parts.append(f"Сообщение: {message.text}")
        
        return "\n".join(context_parts)
    
    def _format_messages(self, messages: List[Message]) -> str:
        """Форматирование сообщений для контекста"""
        formatted = []
        for i, message in enumerate(messages, 1):
            formatted.append(f"Сообщение {i}: {message.text}")
        
        return "\n".join(formatted)
    
    def _count_tokens(self, text: str) -> int:
        """Примерный подсчет токенов (1 токен ≈ 4 символа)"""
        return len(text) // 4
    
    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """Обрезка текста до указанного количества токенов"""
        max_chars = max_tokens * 4  # Примерное соотношение
        if len(text) <= max_chars:
            return text
        
        # Обрезаем по словам
        words = text.split()
        truncated_words = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                truncated_words.append(word)
                current_length += len(word) + 1
            else:
                break
        
        return " ".join(truncated_words)
    
    def extract_key_insights(self, messages: List[str]) -> Dict[str, List[str]]:
        """Извлечение ключевых инсайтов из диалога"""
        insights = {
            'goals': [],
            'problems': [],
            'fears': [],
            'interests': [],
            'context': []
        }
        
        for message in messages:
            text_lower = message.lower()
            
            # Цели и мечты
            if any(word in text_lower for word in ['хочу', 'мечтаю', 'цель', 'планирую']):
                insights['goals'].append(message)
            
            # Проблемы
            if any(word in text_lower for word in ['проблема', 'трудно', 'сложно', 'не получается']):
                insights['problems'].append(message)
            
            # Страхи
            if any(word in text_lower for word in ['боюсь', 'страшно', 'тревожно', 'волнуюсь']):
                insights['fears'].append(message)
            
            # Интересы
            if any(word in text_lower for word in ['интересно', 'нравится', 'люблю', 'увлекаюсь']):
                insights['interests'].append(message)
            
            # Общий контекст
            if len(message) > 50:  # Более развернутые сообщения
                insights['context'].append(message)
        
        return insights
    
    def create_summary(self, messages: List[str]) -> str:
        """Создание краткого резюме диалога"""
        insights = self.extract_key_insights(messages)
        
        summary_parts = []
        
        if insights['goals']:
            summary_parts.append(f"Цели: {insights['goals'][0][:100]}...")
        
        if insights['problems']:
            summary_parts.append(f"Проблемы: {insights['problems'][0][:100]}...")
        
        if insights['fears']:
            summary_parts.append(f"Страхи: {insights['fears'][0][:100]}...")
        
        if insights['interests']:
            summary_parts.append(f"Интересы: {insights['interests'][0][:100]}...")
        
        if not summary_parts:
            # Если нет ключевых инсайтов, берем последние сообщения
            recent_messages = messages[-3:] if len(messages) > 3 else messages
            summary_parts.append(f"Недавний диалог: {' '.join(recent_messages)[:200]}...")
        
        return " | ".join(summary_parts)