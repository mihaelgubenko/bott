"""
Система адаптивных промптов для HR-психоаналитического бота
Автоматически адаптирует промпты на основе профиля пользователя и контекста
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)

class UserStyle(Enum):
    """Стили общения пользователей"""
    FORMAL = "formal"
    CASUAL = "casual"
    SUPPORTIVE = "supportive"
    ANALYTICAL = "analytical"
    EMOTIONAL = "emotional"
    PRACTICAL = "practical"

class PromptType(Enum):
    """Типы промптов"""
    PSYCHOLOGY_CONSULTATION = "psychology_consultation"
    EXPRESS_ANALYSIS = "express_analysis"
    FULL_ANALYSIS = "full_analysis"
    CAREER_ADVICE = "career_advice"
    EMOTIONAL_SUPPORT = "emotional_support"
    GENERAL_CHAT = "general_chat"

@dataclass
class AdaptivePrompt:
    """Адаптивный промпт"""
    base_prompt: str
    adaptations: List[str]
    user_style: UserStyle
    context_adaptations: List[str]
    final_prompt: str

@dataclass
class UserContext:
    """Контекст пользователя для адаптации"""
    user_id: int
    preferred_style: UserStyle
    psychological_traits: Dict[str, float]
    communication_patterns: Dict[str, float]
    interests: List[str]
    session_context: Dict[str, Any]
    conversation_history: List[str]

class AdaptivePromptSystem:
    """Система адаптивных промптов"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.style_adaptations = self._load_style_adaptations()
        self.context_rules = self._load_context_rules()
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_style_adaptations(self) -> Dict[UserStyle, Dict[str, str]]:
        """Загрузка адаптаций для разных стилей общения"""
        return {
            UserStyle.FORMAL: {
                'tone': 'Используй формальный, профессиональный тон.',
                'language': 'Применяй деловую лексику и структурированные формулировки.',
                'approach': 'Фокусируйся на фактах и профессиональном анализе.',
                'greeting': 'Обращайся вежливо и уважительно.',
                'closing': 'Завершай сообщения профессионально.'
            },
            UserStyle.CASUAL: {
                'tone': 'Используй дружелюбный, неформальный тон.',
                'language': 'Применяй простую, понятную лексику.',
                'approach': 'Общайся как с другом, используй эмодзи.',
                'greeting': 'Приветствуй тепло и непринужденно.',
                'closing': 'Завершай сообщения дружелюбно.'
            },
            UserStyle.SUPPORTIVE: {
                'tone': 'Используй эмпатичный, поддерживающий тон.',
                'language': 'Применяй мягкие, понимающие формулировки.',
                'approach': 'Делай акцент на поддержке и понимании.',
                'greeting': 'Начинай с выражения понимания и поддержки.',
                'closing': 'Завершай ободряющими словами.'
            },
            UserStyle.ANALYTICAL: {
                'tone': 'Используй научный, аналитический тон.',
                'language': 'Применяй точную терминологию и структурированный подход.',
                'approach': 'Предоставляй детальный анализ и обоснования.',
                'greeting': 'Начинай с четкой постановки задачи.',
                'closing': 'Завершай выводами и рекомендациями.'
            },
            UserStyle.EMOTIONAL: {
                'tone': 'Используй эмоционально окрашенный, выразительный тон.',
                'language': 'Применяй богатую эмоциональную лексику.',
                'approach': 'Фокусируйся на чувствах и эмоциональном состоянии.',
                'greeting': 'Начинай с выражения понимания чувств.',
                'closing': 'Завершай эмоциональной поддержкой.'
            },
            UserStyle.PRACTICAL: {
                'tone': 'Используй практичный, результативный тон.',
                'language': 'Применяй конкретную, действенную лексику.',
                'approach': 'Фокусируйся на практических решениях и действиях.',
                'greeting': 'Начинай с понимания практических потребностей.',
                'closing': 'Завершай конкретными шагами.'
            }
        }
    
    def _load_context_rules(self) -> Dict[str, List[str]]:
        """Загрузка правил адаптации по контексту"""
        return {
            'high_anxiety': [
                'Будь особенно деликатным и успокаивающим.',
                'Избегай резких формулировок.',
                'Предлагай техники релаксации.',
                'Делай акцент на безопасности и поддержке.'
            ],
            'high_depression': [
                'Проявляй максимальную эмпатию и понимание.',
                'Избегай токсичной позитивности.',
                'Предлагай небольшие, достижимые шаги.',
                'Напоминай о важности профессиональной помощи.'
            ],
            'high_ambition': [
                'Фокусируйся на мотивации и достижениях.',
                'Предлагай амбициозные, но реалистичные цели.',
                'Подчеркивай возможности роста.',
                'Давай практические советы по развитию.'
            ],
            'career_focus': [
                'Концентрируйся на профессиональном развитии.',
                'Предлагай конкретные карьерные шаги.',
                'Анализируй навыки и компетенции.',
                'Давай советы по поиску работы.'
            ],
            'relationship_issues': [
                'Фокусируйся на коммуникации и понимании.',
                'Предлагай техники разрешения конфликтов.',
                'Анализируй паттерны отношений.',
                'Давай советы по улучшению отношений.'
            ],
            'family_matters': [
                'Проявляй особую деликатность.',
                'Учитывай семейную динамику.',
                'Предлагай семейные решения.',
                'Рекомендуй семейную терапию при необходимости.'
            ]
        }
    
    def _load_prompt_templates(self) -> Dict[PromptType, str]:
        """Загрузка базовых шаблонов промптов"""
        return {
            PromptType.PSYCHOLOGY_CONSULTATION: """
Ты — опытный психолог с большим сердцем. Твоя главная задача - ПОДДЕРЖАТЬ и ПОНИМАТЬ.

ИСТОРИЯ РАЗГОВОРА:
{conversation_context}

ТЕКУЩЕЕ СООБЩЕНИЕ КЛИЕНТА:
{user_message}

ТВОЯ РОЛЬ: Друг-психолог, который всегда на стороне человека и ПОМНИТ весь разговор.

ПРИНЦИПЫ:
- СНАЧАЛА прояви эмпатию и понимание
- УЧИТЫВАЙ всю историю разговора
- НЕ давай советы, если человек не просит
- Поддерживай эмоционально
- Будь теплым и человечным

ФОРМАТ ОТВЕТА:
💙 Эмпатичный ответ (понимание чувств с учетом контекста)
🤗 Поддержка и принятие
💡 Мягкие рекомендации (если уместно)

СТИЛЬ: Теплый, понимающий, как разговор с близким другом, который помнит всё. 150-300 слов.
""",
            
            PromptType.EXPRESS_ANALYSIS: """
Ты — профессиональный HR-психоаналитик и карьерный консультант.

ДИАЛОГ КЛИЕНТА ({message_count} сообщений):
{conversation}

ЗАДАЧА: Проведи экспресс-анализ личности на основе диалога.

МЕТОДОЛОГИЯ:
- Психоанализ (Фрейд): защитные механизмы, бессознательные мотивы
- Аналитическая психология (Юнг): архетипы, типы личности
- MBTI: предпочтения в восприятии и принятии решений
- Big Five: основные черты личности

ФОРМАТ ОТВЕТА:
🎯 ЭКСПРЕСС-ПРОФИЛЬ

🧠 Психотип: [краткое описание на основе Юнга/Фрейда]
📊 Основные черты: [2-3 ключевые характеристики]
💼 Подходящие сферы: [3-4 области деятельности]
🎓 Рекомендации по обучению: [конкретные направления]
⚠️ Зоны развития: [что стоит развивать]

СТИЛЬ: Профессиональный, эмпатичный, конкретный. Максимум 300 слов.
""",
            
            PromptType.FULL_ANALYSIS: """
Ты — ведущий психоаналитик и HR-эксперт с 20-летним опытом.

ДЕТАЛЬНЫЕ ОТВЕТЫ КЛИЕНТА:
{answers_text}

ПРОВЕДИ ГЛУБОКИЙ ПСИХОАНАЛИЗ:

🧠 ПСИХОАНАЛИТИЧЕСКИЙ ПРОФИЛЬ:
- Структура личности (Ид/Эго/Суперэго)
- Защитные механизмы
- Бессознательные конфликты
- Травмы и их влияние

🎭 АРХЕТИПЫ И ТИПОЛОГИЯ:
- Доминирующий архетип по Юнгу
- MBTI тип с обоснованием
- Темперамент и особенности

📊 BIG FIVE (OCEAN):
- Открытость: [1-10] + обоснование
- Добросовестность: [1-10] + обоснование  
- Экстраверсия: [1-10] + обоснование
- Доброжелательность: [1-10] + обоснование
- Нейротизм: [1-10] + обоснование

💼 HR-РЕКОМЕНДАЦИИ:
- Подходящие роли и позиции
- Стиль управления/работы
- Мотивационные факторы
- Потенциальные риски

🎓 ОБРАЗОВАТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:
- Конкретные направления обучения
- Форматы обучения (очное/заочное)
- Дополнительные навыки
- Карьерная траектория

🔮 ПРОГНОЗ РАЗВИТИЯ:
- Как будет развиваться личность
- Ключевые точки роста
- Рекомендации по саморазвитию

СТИЛЬ: Профессиональный, детальный, практичный. 800-1200 слов.
"""
        }
    
    def generate_adaptive_prompt(self, user_context: UserContext, 
                                prompt_type: PromptType,
                                additional_context: Dict[str, Any] = None) -> AdaptivePrompt:
        """Генерация адаптивного промпта"""
        
        # Получаем базовый промпт
        base_prompt = self.prompt_templates.get(prompt_type, "")
        
        # Адаптации по стилю пользователя
        style_adaptations = self._get_style_adaptations(user_context.preferred_style)
        
        # Адаптации по психологическому профилю
        psychological_adaptations = self._get_psychological_adaptations(user_context.psychological_traits)
        
        # Адаптации по контексту сессии
        session_adaptations = self._get_session_adaptations(user_context.session_context)
        
        # Адаптации по истории разговора
        conversation_adaptations = self._get_conversation_adaptations(user_context.conversation_history)
        
        # Дополнительные адаптации
        additional_adaptations = self._get_additional_adaptations(additional_context or {})
        
        # Объединяем все адаптации
        all_adaptations = (
            style_adaptations + 
            psychological_adaptations + 
            session_adaptations + 
            conversation_adaptations + 
            additional_adaptations
        )
        
        # Создаем финальный промпт
        final_prompt = self._build_final_prompt(base_prompt, all_adaptations, user_context)
        
        return AdaptivePrompt(
            base_prompt=base_prompt,
            adaptations=all_adaptations,
            user_style=user_context.preferred_style,
            context_adaptations=session_adaptations,
            final_prompt=final_prompt
        )
    
    def _get_style_adaptations(self, user_style: UserStyle) -> List[str]:
        """Получение адаптаций по стилю пользователя"""
        adaptations = self.style_adaptations.get(user_style, {})
        return list(adaptations.values())
    
    def _get_psychological_adaptations(self, traits: Dict[str, float]) -> List[str]:
        """Получение адаптаций по психологическому профилю"""
        adaptations = []
        
        for trait, value in traits.items():
            if value > 0.7:  # Высокий уровень черты
                trait_adaptations = self.context_rules.get(f'high_{trait}', [])
                adaptations.extend(trait_adaptations)
            elif value < 0.3:  # Низкий уровень черты
                # Специальные адаптации для низких значений
                if trait == 'openness':
                    adaptations.append('Предлагай более творческие и нестандартные решения.')
                elif trait == 'conscientiousness':
                    adaptations.append('Делай акцент на гибкости и адаптивности.')
        
        return adaptations
    
    def _get_session_adaptations(self, session_context: Dict[str, Any]) -> List[str]:
        """Получение адаптаций по контексту сессии"""
        adaptations = []
        
        # Адаптации по типу запроса
        if session_context.get('request_type') == 'career_advice':
            adaptations.extend(self.context_rules.get('career_focus', []))
        
        if session_context.get('request_type') == 'relationship_help':
            adaptations.extend(self.context_rules.get('relationship_issues', []))
        
        if session_context.get('request_type') == 'family_problems':
            adaptations.extend(self.context_rules.get('family_matters', []))
        
        # Адаптации по длине сессии
        session_length = session_context.get('session_length', 0)
        if session_length > 10:
            adaptations.append('Учитывай, что это длинная сессия - пользователь активно взаимодействует.')
        elif session_length < 3:
            adaptations.append('Это начало разговора - будь особенно приветливым и заинтересованным.')
        
        # Адаптации по времени суток
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            adaptations.append('Учитывай, что позднее время - будь особенно деликатным.')
        
        return adaptations
    
    def _get_conversation_adaptations(self, conversation_history: List[str]) -> List[str]:
        """Получение адаптаций по истории разговора"""
        adaptations = []
        
        if not conversation_history:
            return adaptations
        
        # Анализируем последние сообщения
        recent_messages = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
        
        # Поиск эмоциональных маркеров
        emotional_words = ['грустно', 'радость', 'тревога', 'страх', 'злость', 'счастье']
        has_emotional_content = any(
            any(word in msg.lower() for word in emotional_words) 
            for msg in recent_messages
        )
        
        if has_emotional_content:
            adaptations.append('Пользователь проявляет эмоциональность - будь особенно эмпатичным.')
        
        # Поиск вопросов
        question_count = sum(msg.count('?') for msg in recent_messages)
        if question_count > 2:
            adaptations.append('Пользователь задает много вопросов - давай подробные ответы.')
        
        # Поиск благодарности
        gratitude_words = ['спасибо', 'благодарю', 'помогло', 'понравилось']
        has_gratitude = any(
            any(word in msg.lower() for word in gratitude_words) 
            for msg in recent_messages
        )
        
        if has_gratitude:
            adaptations.append('Пользователь благодарит - продолжай в том же духе.')
        
        return adaptations
    
    def _get_additional_adaptations(self, additional_context: Dict[str, Any]) -> List[str]:
        """Получение дополнительных адаптаций"""
        adaptations = []
        
        # Адаптации по настроению
        sentiment = additional_context.get('sentiment')
        if sentiment == 'negative':
            adaptations.append('Пользователь в негативном настроении - усиль поддержку.')
        elif sentiment == 'positive':
            adaptations.append('Пользователь в позитивном настроении - развивай тему.')
        
        # Адаптации по интересам
        interests = additional_context.get('interests', [])
        if 'психология' in interests:
            adaptations.append('Пользователь интересуется психологией - используй профессиональную терминологию.')
        if 'карьера' in interests:
            adaptations.append('Пользователь интересуется карьерой - фокусируйся на профессиональном развитии.')
        
        return adaptations
    
    def _build_final_prompt(self, base_prompt: str, adaptations: List[str], 
                           user_context: UserContext) -> str:
        """Сборка финального промпта"""
        
        # Если нет адаптаций, возвращаем базовый промпт
        if not adaptations:
            return base_prompt
        
        # Создаем секцию адаптаций
        adaptations_text = "\n".join([f"- {adaptation}" for adaptation in adaptations])
        
        # Добавляем информацию о пользователе
        user_info = f"""
ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
- Стиль общения: {user_context.preferred_style.value}
- Основные интересы: {', '.join(user_context.interests[:3]) if user_context.interests else 'не определены'}
- Психологические особенности: {self._format_psychological_traits(user_context.psychological_traits)}
"""
        
        # Объединяем все части
        final_prompt = f"""{base_prompt}

{user_info}

ДОПОЛНИТЕЛЬНЫЕ АДАПТАЦИИ:
{adaptations_text}

ВАЖНО: Учитывай все указанные адаптации при формировании ответа.
"""
        
        return final_prompt
    
    def _format_psychological_traits(self, traits: Dict[str, float]) -> str:
        """Форматирование психологических черт"""
        if not traits:
            return 'не определены'
        
        formatted_traits = []
        for trait, value in traits.items():
            if value > 0.6:
                formatted_traits.append(f"высокий {trait}")
            elif value < 0.4:
                formatted_traits.append(f"низкий {trait}")
        
        return ', '.join(formatted_traits) if formatted_traits else 'сбалансированные'
    
    def detect_user_style(self, conversation_history: List[str], 
                         psychological_traits: Dict[str, float] = None) -> UserStyle:
        """Автоматическое определение стиля пользователя"""
        
        if not conversation_history:
            return UserStyle.BALANCED
        
        # Анализируем последние сообщения
        recent_messages = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        text_sample = " ".join(recent_messages).lower()
        
        # Подсчет индикаторов стилей
        style_scores = {
            UserStyle.FORMAL: 0,
            UserStyle.CASUAL: 0,
            UserStyle.SUPPORTIVE: 0,
            UserStyle.ANALYTICAL: 0,
            UserStyle.EMOTIONAL: 0,
            UserStyle.PRACTICAL: 0
        }
        
        # Формальный стиль
        formal_indicators = ['пожалуйста', 'спасибо', 'извините', 'благодарю', 'уважаемый']
        style_scores[UserStyle.FORMAL] = sum(1 for word in formal_indicators if word in text_sample)
        
        # Неформальный стиль
        casual_indicators = ['привет', 'спс', 'ок', 'давай', 'круто', 'супер']
        style_scores[UserStyle.CASUAL] = sum(1 for word in casual_indicators if word in text_sample)
        
        # Поддерживающий стиль
        supportive_indicators = ['помоги', 'поддержка', 'трудно', 'сложно', 'не получается']
        style_scores[UserStyle.SUPPORTIVE] = sum(1 for word in supportive_indicators if word in text_sample)
        
        # Аналитический стиль
        analytical_indicators = ['анализ', 'данные', 'статистика', 'исследование', 'логично']
        style_scores[UserStyle.ANALYTICAL] = sum(1 for word in analytical_indicators if word in text_sample)
        
        # Эмоциональный стиль
        emotional_indicators = ['чувствую', 'эмоции', 'переживаю', 'волнуюсь', 'радуюсь']
        style_scores[UserStyle.EMOTIONAL] = sum(1 for word in emotional_indicators if word in text_sample)
        
        # Практический стиль
        practical_indicators = ['как сделать', 'что делать', 'решение', 'действие', 'шаг']
        style_scores[UserStyle.PRACTICAL] = sum(1 for word in practical_indicators if word in text_sample)
        
        # Учитываем психологические черты
        if psychological_traits:
            if psychological_traits.get('anxiety', 0) > 0.7:
                style_scores[UserStyle.SUPPORTIVE] += 2
            if psychological_traits.get('openness', 0) > 0.7:
                style_scores[UserStyle.ANALYTICAL] += 1
            if psychological_traits.get('conscientiousness', 0) > 0.7:
                style_scores[UserStyle.PRACTICAL] += 1
        
        # Возвращаем стиль с максимальным счетом
        return max(style_scores, key=style_scores.get)
    
    def get_adaptive_prompt_statistics(self) -> Dict[str, Any]:
        """Получение статистики использования адаптивных промптов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу для статистики адаптивных промптов, если её нет
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adaptive_prompt_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prompt_type TEXT NOT NULL,
                user_style TEXT NOT NULL,
                adaptations_count INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Получаем статистику по стилям
        cursor.execute('''
            SELECT user_style, COUNT(*) as usage_count 
            FROM adaptive_prompt_usage 
            GROUP BY user_style
        ''')
        style_stats = dict(cursor.fetchall())
        
        # Получаем статистику по типам промптов
        cursor.execute('''
            SELECT prompt_type, COUNT(*) as usage_count 
            FROM adaptive_prompt_usage 
            GROUP BY prompt_type
        ''')
        prompt_type_stats = dict(cursor.fetchall())
        
        # Получаем среднее количество адаптаций
        cursor.execute('SELECT AVG(adaptations_count) FROM adaptive_prompt_usage')
        avg_adaptations = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'style_distribution': style_stats,
            'prompt_type_distribution': prompt_type_stats,
            'average_adaptations': round(avg_adaptations, 2),
            'total_usage': sum(style_stats.values())
        }
    
    def record_prompt_usage(self, user_id: int, prompt_type: PromptType, 
                           user_style: UserStyle, adaptations_count: int):
        """Запись использования адаптивного промпта"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO adaptive_prompt_usage 
            (user_id, prompt_type, user_style, adaptations_count)
            VALUES (?, ?, ?, ?)
        ''', (user_id, prompt_type.value, user_style.value, adaptations_count))
        
        conn.commit()
        conn.close()

def get_adaptive_prompt_system(db_path: str = 'psychoanalyst.db') -> AdaptivePromptSystem:
    """Фабричная функция для получения системы адаптивных промптов"""
    return AdaptivePromptSystem(db_path)

# Пример использования
if __name__ == "__main__":
    adaptive_system = get_adaptive_prompt_system()
    
    # Создаем контекст пользователя
    user_context = UserContext(
        user_id=12345,
        preferred_style=UserStyle.SUPPORTIVE,
        psychological_traits={
            'anxiety': 0.8,
            'depression': 0.3,
            'ambition': 0.6
        },
        communication_patterns={
            'message_length': 25,
            'question_frequency': 0.3
        },
        interests=['психология', 'карьера'],
        session_context={
            'session_length': 5,
            'request_type': 'career_advice'
        },
        conversation_history=[
            "Привет! У меня проблемы на работе",
            "Не знаю, что делать с начальником",
            "Может быть, мне стоит уволиться?"
        ]
    )
    
    # Генерируем адаптивный промпт
    adaptive_prompt = adaptive_system.generate_adaptive_prompt(
        user_context=user_context,
        prompt_type=PromptType.PSYCHOLOGY_CONSULTATION,
        additional_context={
            'sentiment': 'negative',
            'interests': ['карьера']
        }
    )
    
    print("Адаптивный промпт:")
    print(adaptive_prompt.final_prompt)
    
    # Записываем использование
    adaptive_system.record_prompt_usage(
        user_id=12345,
        prompt_type=PromptType.PSYCHOLOGY_CONSULTATION,
        user_style=UserStyle.SUPPORTIVE,
        adaptations_count=len(adaptive_prompt.adaptations)
    )
    
    # Получаем статистику
    stats = adaptive_system.get_adaptive_prompt_statistics()
    print("\nСтатистика адаптивных промптов:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))