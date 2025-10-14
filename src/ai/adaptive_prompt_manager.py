"""
Менеджер адаптивных промптов для оптимизации запросов к ИИ
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PromptType(Enum):
    """Типы промптов"""
    EXPRESS_ANALYSIS = "express_analysis"
    FULL_ANALYSIS = "full_analysis"
    PSYCHOLOGY_CONSULTATION = "psychology_consultation"
    CAREER_CONSULTATION = "career_consultation"
    EMOTIONAL_SUPPORT = "emotional_support"
    SELF_ESTEEM_ANALYSIS = "self_esteem_analysis"

class PromptLength(Enum):
    """Длины промптов"""
    SHORT = "short"      # ~200 токенов
    MEDIUM = "medium"    # ~400 токенов
    LONG = "long"        # ~600 токенов
    EXTENDED = "extended" # ~800 токенов

@dataclass
class PromptTemplate:
    """Шаблон промпта"""
    id: str
    type: PromptType
    length: PromptLength
    template: str
    description: str
    estimated_tokens: int
    active: bool = True

class AdaptivePromptManager:
    """Менеджер адаптивных промптов"""
    
    def __init__(self, config):
        self.config = config
        self.templates = self._load_default_templates()
        self.user_preferences = {}  # Предпочтения пользователей
    
    def _load_default_templates(self) -> Dict[str, PromptTemplate]:
        """Загрузка стандартных шаблонов промптов"""
        templates = {}
        
        # Экспресс-анализ - короткий
        templates["express_analysis_short"] = PromptTemplate(
            id="express_analysis_short",
            type=PromptType.EXPRESS_ANALYSIS,
            length=PromptLength.SHORT,
            template="""Ты — HR-психоаналитик. Проведи краткий анализ личности.

ДИАЛОГ: {conversation}

ФОРМАТ:
🧠 Психотип: [кратко]
💼 Подходящие сферы: [2-3 области]
🎯 Рекомендации: [конкретно]

СТИЛЬ: Профессиональный, до 150 слов.""",
            description="Краткий экспресс-анализ",
            estimated_tokens=200
        )
        
        # Экспресс-анализ - средний
        templates["express_analysis_medium"] = PromptTemplate(
            id="express_analysis_medium",
            type=PromptType.EXPRESS_ANALYSIS,
            length=PromptLength.MEDIUM,
            template="""Ты — профессиональный HR-психоаналитик и карьерный консультант.

ДИАЛОГ КЛИЕНТА ({message_count} сообщений):
{conversation}

ЗАДАЧА: Проведи экспресс-анализ личности.

МЕТОДОЛОГИЯ:
- Психоанализ (Фрейд): защитные механизмы
- Аналитическая психология (Юнг): архетипы
- MBTI: предпочтения в принятии решений
- Big Five: основные черты личности

ФОРМАТ ОТВЕТА:
🎯 ЭКСПРЕСС-ПРОФИЛЬ

🧠 Психотип: [краткое описание]
📊 Основные черты: [2-3 характеристики]
💼 Подходящие сферы: [3-4 области]
🎓 Рекомендации: [конкретные направления]
⚠️ Зоны развития: [что развивать]

СТИЛЬ: Профессиональный, эмпатичный. До 300 слов.""",
            description="Стандартный экспресс-анализ",
            estimated_tokens=400
        )
        
        # Экспресс-анализ - длинный
        templates["express_analysis_long"] = PromptTemplate(
            id="express_analysis_long",
            type=PromptType.EXPRESS_ANALYSIS,
            length=PromptLength.LONG,
            template="""Ты — ведущий HR-психоаналитик с 20-летним опытом.

ДЕТАЛЬНЫЙ ДИАЛОГ КЛИЕНТА ({message_count} сообщений):
{conversation}

КОНТЕКСТ: {context_summary}

ЗАДАЧА: Проведи глубокий экспресс-анализ личности.

МЕТОДОЛОГИЯ:
- Психоанализ (Фрейд): защитные механизмы, бессознательные мотивы
- Аналитическая психология (Юнг): архетипы, типы личности
- MBTI: предпочтения в восприятии и принятии решений
- Big Five: основные черты личности
- Анализ речевых паттернов и эмоциональных индикаторов

ФОРМАТ ОТВЕТА:
🎯 ДЕТАЛЬНЫЙ ЭКСПРЕСС-ПРОФИЛЬ

🧠 Психотип: [подробное описание на основе Юнга/Фрейда]
📊 Основные черты: [3-4 ключевые характеристики с примерами]
💼 Подходящие сферы: [4-5 областей с обоснованием]
🎓 Рекомендации по обучению: [конкретные направления и форматы]
⚠️ Зоны развития: [что стоит развивать и как]
💡 Карьерные перспективы: [потенциал роста]

СТИЛЬ: Профессиональный, эмпатичный, конкретный. До 500 слов.""",
            description="Детальный экспресс-анализ",
            estimated_tokens=600
        )
        
        # Психологическая консультация - короткая
        templates["psychology_consultation_short"] = PromptTemplate(
            id="psychology_consultation_short",
            type=PromptType.PSYCHOLOGY_CONSULTATION,
            length=PromptLength.SHORT,
            template="""Ты — психолог-консультант. Поддержи и пойми клиента.

СООБЩЕНИЕ: {user_message}

ОТВЕТ:
💙 Понимание чувств
🤗 Поддержка
💡 Мягкий совет

СТИЛЬ: Теплый, до 100 слов.""",
            description="Краткая психологическая поддержка",
            estimated_tokens=150
        )
        
        # Психологическая консультация - средняя
        templates["psychology_consultation_medium"] = PromptTemplate(
            id="psychology_consultation_medium",
            type=PromptType.PSYCHOLOGY_CONSULTATION,
            length=PromptLength.MEDIUM,
            template="""Ты — опытный психолог с большим сердцем.

ИСТОРИЯ РАЗГОВОРА:
{conversation_context}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{user_message}

ТВОЯ РОЛЬ: Друг-психолог, который помнит весь разговор.

ПРИНЦИПЫ:
- СНАЧАЛА прояви эмпатию и понимание
- УЧИТЫВАЙ всю историю разговора
- НЕ давай советы, если не просят
- Поддерживай эмоционально

ФОРМАТ ОТВЕТА:
💙 Эмпатичный ответ (с учетом контекста)
🤗 Поддержка и принятие
💡 Мягкие рекомендации (если уместно)

СТИЛЬ: Теплый, понимающий. До 250 слов.""",
            description="Стандартная психологическая поддержка",
            estimated_tokens=300
        )
        
        # Карьерная консультация - средняя
        templates["career_consultation_medium"] = PromptTemplate(
            id="career_consultation_medium",
            type=PromptType.CAREER_CONSULTATION,
            length=PromptLength.MEDIUM,
            template="""Ты — HR-консультант с 15-летним опытом.

СООБЩЕНИЕ КЛИЕНТА:
{user_message}

КОНТЕКСТ: {context_summary}

ТВОЯ РОЛЬ: Эксперт по карьере и развитию.

ФОКУС:
- Конкретные техники и методики
- Практические советы
- Карьерные стратегии
- Образовательные направления

ФОРМАТ ОТВЕТА:
💼 Практические рекомендации
🎯 Конкретные техники
📈 Карьерные стратегии
🎓 Образовательные направления

СТИЛЬ: Профессиональный, конкретный. До 300 слов.""",
            description="Карьерная консультация",
            estimated_tokens=350
        )
        
        return templates
    
    def get_optimal_prompt(
        self, 
        prompt_type: PromptType, 
        available_tokens: int,
        user_id: Optional[int] = None,
        context: Optional[Dict] = None
    ) -> Tuple[str, str]:
        """Получение оптимального промпта на основе доступных токенов"""
        
        # Получаем предпочтения пользователя
        user_prefs = self.user_preferences.get(user_id, {})
        
        # Фильтруем шаблоны по типу
        type_templates = {
            k: v for k, v in self.templates.items() 
            if v.type == prompt_type and v.active
        }
        
        if not type_templates:
            logger.error(f"Нет доступных шаблонов для типа {prompt_type}")
            return "", "default"
        
        # Выбираем оптимальную длину
        optimal_length = self._select_optimal_length(available_tokens, user_prefs)
        
        # Ищем шаблон подходящей длины
        suitable_templates = [
            t for t in type_templates.values() 
            if t.length == optimal_length and t.estimated_tokens <= available_tokens
        ]
        
        if not suitable_templates:
            # Если нет подходящих, берем самый короткий
            suitable_templates = [
                t for t in type_templates.values() 
                if t.estimated_tokens <= available_tokens
            ]
            suitable_templates.sort(key=lambda x: x.estimated_tokens)
        
        if not suitable_templates:
            # Если ничего не подходит, берем самый короткий
            suitable_templates = [min(type_templates.values(), key=lambda x: x.estimated_tokens)]
        
        selected_template = suitable_templates[0]
        
        # Форматируем промпт
        formatted_prompt = self._format_prompt(selected_template, context or {})
        
        return formatted_prompt, selected_template.id
    
    def _select_optimal_length(self, available_tokens: int, user_prefs: Dict) -> PromptLength:
        """Выбор оптимальной длины промпта"""
        
        # Учитываем предпочтения пользователя
        preferred_length = user_prefs.get('preferred_length')
        if preferred_length:
            try:
                return PromptLength(preferred_length)
            except ValueError:
                pass
        
        # Выбираем на основе доступных токенов
        if available_tokens >= 600:
            return PromptLength.LONG
        elif available_tokens >= 400:
            return PromptLength.MEDIUM
        else:
            return PromptLength.SHORT
    
    def _format_prompt(self, template: PromptTemplate, context: Dict) -> str:
        """Форматирование промпта с контекстом"""
        try:
            return template.template.format(**context)
        except KeyError as e:
            logger.error(f"Ошибка форматирования промпта {template.id}: {e}")
            # Возвращаем базовый шаблон без форматирования
            return template.template
    
    def update_user_preferences(self, user_id: int, preferences: Dict):
        """Обновление предпочтений пользователя"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id].update(preferences)
        logger.info(f"Обновлены предпочтения пользователя {user_id}: {preferences}")
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """Получение предпочтений пользователя"""
        return self.user_preferences.get(user_id, {})
    
    def add_custom_template(self, template: PromptTemplate):
        """Добавление пользовательского шаблона"""
        self.templates[template.id] = template
        logger.info(f"Добавлен пользовательский шаблон: {template.id}")
    
    def deactivate_template(self, template_id: str):
        """Деактивация шаблона"""
        if template_id in self.templates:
            self.templates[template_id].active = False
            logger.info(f"Деактивирован шаблон: {template_id}")
    
    def get_template_stats(self) -> Dict[str, Dict]:
        """Получение статистики по шаблонам"""
        stats = {}
        
        for template_id, template in self.templates.items():
            stats[template_id] = {
                'type': template.type.value,
                'length': template.length.value,
                'estimated_tokens': template.estimated_tokens,
                'active': template.active,
                'description': template.description
            }
        
        return stats
    
    def optimize_for_user(self, user_id: int, usage_history: List[Dict]) -> Dict:
        """Оптимизация промптов для конкретного пользователя на основе истории"""
        
        # Анализируем паттерны использования
        patterns = self._analyze_usage_patterns(usage_history)
        
        # Рекомендации по оптимизации
        recommendations = {
            'preferred_length': self._recommend_length(patterns),
            'preferred_style': self._recommend_style(patterns),
            'optimization_suggestions': self._get_optimization_suggestions(patterns)
        }
        
        # Обновляем предпочтения
        self.update_user_preferences(user_id, recommendations)
        
        return recommendations
    
    def _analyze_usage_patterns(self, usage_history: List[Dict]) -> Dict:
        """Анализ паттернов использования"""
        patterns = {
            'avg_response_length': 0,
            'preferred_prompt_types': [],
            'truncation_rate': 0,
            'user_satisfaction': 0
        }
        
        if not usage_history:
            return patterns
        
        # Анализируем длину ответов
        response_lengths = [h.get('response_length', 0) for h in usage_history]
        patterns['avg_response_length'] = sum(response_lengths) / len(response_lengths)
        
        # Анализируем типы промптов
        prompt_types = [h.get('prompt_type') for h in usage_history if h.get('prompt_type')]
        patterns['preferred_prompt_types'] = list(set(prompt_types))
        
        # Анализируем обрезание ответов
        truncated_count = sum(1 for h in usage_history if h.get('truncated', False))
        patterns['truncation_rate'] = truncated_count / len(usage_history)
        
        # Анализируем удовлетворенность
        satisfaction_scores = [h.get('satisfaction', 0) for h in usage_history if h.get('satisfaction')]
        if satisfaction_scores:
            patterns['user_satisfaction'] = sum(satisfaction_scores) / len(satisfaction_scores)
        
        return patterns
    
    def _recommend_length(self, patterns: Dict) -> str:
        """Рекомендация длины промпта"""
        avg_length = patterns.get('avg_response_length', 0)
        truncation_rate = patterns.get('truncation_rate', 0)
        
        if truncation_rate > 0.3:
            return PromptLength.SHORT.value
        elif avg_length > 400:
            return PromptLength.LONG.value
        else:
            return PromptLength.MEDIUM.value
    
    def _recommend_style(self, patterns: Dict) -> str:
        """Рекомендация стиля промпта"""
        satisfaction = patterns.get('user_satisfaction', 0)
        
        if satisfaction > 4.0:
            return "detailed"  # Пользователь любит детальные ответы
        else:
            return "concise"   # Пользователь предпочитает краткие ответы
    
    def _get_optimization_suggestions(self, patterns: Dict) -> List[str]:
        """Получение предложений по оптимизации"""
        suggestions = []
        
        if patterns.get('truncation_rate', 0) > 0.2:
            suggestions.append("Рекомендуется использовать более короткие промпты")
        
        if patterns.get('avg_response_length', 0) < 200:
            suggestions.append("Можно увеличить детализацию ответов")
        
        if patterns.get('user_satisfaction', 0) < 3.0:
            suggestions.append("Стоит адаптировать стиль под предпочтения пользователя")
        
        return suggestions