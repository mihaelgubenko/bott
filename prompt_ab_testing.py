"""
Модуль A/B тестирования промптов для оптимизации качества ответов ИИ
Позволяет тестировать разные варианты промптов и выбирать лучшие
"""

import json
import random
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class PromptType(Enum):
    """Типы промптов для тестирования"""
    EXPRESS_ANALYSIS = "express_analysis"
    FULL_ANALYSIS = "full_analysis"
    PSYCHOLOGY_CONSULTATION = "psychology_consultation"
    CAREER_ADVICE = "career_advice"
    EMOTIONAL_SUPPORT = "emotional_support"

@dataclass
class PromptVariant:
    """Вариант промпта для A/B тестирования"""
    id: str
    type: PromptType
    name: str
    template: str
    description: str
    active: bool = True
    created_at: datetime = None

@dataclass
class TestResult:
    """Результат A/B теста"""
    user_id: int
    prompt_variant_id: str
    prompt_type: PromptType
    user_feedback: Optional[float] = None  # 1-5 rating
    response_quality: Optional[float] = None  # AI-evaluated quality
    user_engagement: Optional[float] = None  # engagement metrics
    conversion: bool = False  # did user convert to paid?
    timestamp: datetime = None

class PromptABTesting:
    """Система A/B тестирования промптов"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.init_database()
        self.load_default_prompts()

    def init_database(self):
        """Инициализация таблиц для A/B тестирования"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица вариантов промптов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompt_variants (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                template TEXT NOT NULL,
                description TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица результатов тестов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ab_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prompt_variant_id TEXT NOT NULL,
                prompt_type TEXT NOT NULL,
                user_feedback REAL,
                response_quality REAL,
                user_engagement REAL,
                conversion BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prompt_variant_id) REFERENCES prompt_variants (id)
            )
        ''')
        
        # Таблица назначений пользователей к вариантам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_variant_assignments (
                user_id INTEGER,
                prompt_type TEXT,
                variant_id TEXT,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, prompt_type)
            )
        ''')
        
        conn.commit()
        conn.close()

    def load_default_prompts(self):
        """Загрузка дефолтных вариантов промптов"""
        default_prompts = [
            # Экспресс-анализ - Вариант A (текущий)
            PromptVariant(
                id="express_analysis_a",
                type=PromptType.EXPRESS_ANALYSIS,
                name="Стандартный экспресс-анализ",
                template="""
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
                description="Текущий стандартный промпт для экспресс-анализа"
            ),
            
            # Экспресс-анализ - Вариант B (более персонализированный)
            PromptVariant(
                id="express_analysis_b",
                type=PromptType.EXPRESS_ANALYSIS,
                name="Персонализированный экспресс-анализ",
                template="""
Ты — опытный психолог-консультант, который работает с каждым клиентом индивидуально.

ИСТОРИЯ ОБЩЕНИЯ ({message_count} сообщений):
{conversation}

ТВОЯ ЗАДАЧА: Создать персональный психологический портрет, обращаясь напрямую к клиенту.

ПОДХОД:
- Найди уникальные особенности именно этого человека
- Используй примеры из его сообщений
- Говори на языке, понятном клиенту
- Подчеркни сильные стороны

СТРУКТУРА ОТВЕТА:
👋 Привет! Вот что я понял о вас:

🌟 Ваш уникальный стиль: [на основе манеры общения]
💪 Ваши суперсилы: [конкретные примеры из диалога]
🎯 Идеальная среда для вас: [где вы будете успешны]
📚 Что изучать: [персональные рекомендации]
🚀 Следующий шаг: [конкретное действие]

СТИЛЬ: Дружелюбный, мотивирующий, с примерами. До 250 слов.
""",
                description="Более персонализированный подход с обращением на 'вы'"
            ),
            
            # Психологическая консультация - Вариант A (обновленный с контекстом)
            PromptVariant(
                id="psychology_consultation_a",
                type=PromptType.PSYCHOLOGY_CONSULTATION,
                name="Стандартная психологическая поддержка",
                template="""
Ты — опытный психолог с большим сердцем. Твоя главная задача - ПОДДЕРЖАТЬ и ПОНИМАТЬ.

ИСТОРИЯ РАЗГОВОРА:
{conversation_context}

ТЕКУЩЕЕ СООБЩЕНИЕ КЛИЕНТА:
{user_message}

ВАЖНО: Если клиент ссылается на предыдущие части разговора ("мы говорили об этом", "выше", "раньше"), обязательно учитывай контекст из истории разговора.

ТВОЯ РОЛЬ: Друг-психолог, который всегда на стороне человека и ПОМНИТ весь разговор.

ПРИНЦИПЫ:
- СНАЧАЛА прояви эмпатию и понимание
- УЧИТЫВАЙ всю историю разговора
- НЕ давай советы, если человек не просит
- Поддерживай эмоционально
- Будь теплым и человечным
- Если человек говорит "не понял" или ссылается на предыдущее - обратись к контексту

ФОРМАТ ОТВЕТА:
💙 Эмпатичный ответ (понимание чувств с учетом контекста)
🤗 Поддержка и принятие
💡 Мягкие рекомендации (если уместно)

СТИЛЬ: Теплый, понимающий, как разговор с близким другом, который помнит всё. 150-300 слов.
""",
                description="Стандартный подход к психологической поддержке с контекстом"
            ),
            
            # Психологическая консультация - Вариант B (с техниками и анализом настроений)
            PromptVariant(
                id="psychology_consultation_b",
                type=PromptType.PSYCHOLOGY_CONSULTATION,
                name="Поддержка с практическими техниками и анализом настроений",
                template="""
Ты — практикующий психолог, который не только поддерживает, но и дает инструменты.

ИСТОРИЯ РАЗГОВОРА:
{conversation_context}

ЧТО ГОВОРИТ КЛИЕНТ:
{user_message}

АНАЛИЗ НАСТРОЕНИЯ: {sentiment_analysis}

ВАЖНО: Если клиент ссылается на предыдущие части разговора, обязательно учитывай контекст из истории разговора.

ТВОЙ ПОДХОД (адаптивный к настроению):
1. Сначала - полное понимание и принятие с учетом эмоционального состояния
2. Затем - практический инструмент или техника, подходящая к настроению
3. Мотивация к действию с учетом психологического состояния

ОТВЕТ ДОЛЖЕН ВКЛЮЧАТЬ:
💝 Эмпатия: "Я понимаю, что вы чувствуете..." (с учетом всего разговора и настроения)
🧘 Техника: Конкретное упражнение, адаптированное под эмоциональное состояние
🌱 Перспектива: Как это поможет в долгосрочной перспективе

СТИЛЬ: Сочетание теплоты и профессионализма, помнящий весь разговор и настроение. 200-350 слов.
""",
                description="Поддержка + практические техники для самопомощи с контекстом и анализом настроений"
            ),
            
            # Психологическая консультация - Вариант C (максимальная эмпатия)
            PromptVariant(
                id="psychology_consultation_c",
                type=PromptType.PSYCHOLOGY_CONSULTATION,
                name="Максимальная эмпатия с учетом настроения",
                template="""
Ты — очень эмпатичный психолог с большим сердцем, который чувствует эмоции клиента.

ИСТОРИЯ РАЗГОВОРА:
{conversation_context}

ЧТО ГОВОРИТ КЛИЕНТ:
{user_message}

АНАЛИЗ НАСТРОЕНИЯ: {sentiment_analysis}

ВАЖНО: Если клиент ссылается на предыдущие части разговора, обязательно учитывай контекст из истории разговора.

ТВОЯ СУПЕРСИЛА - ЭМПАТИЯ:
- Чувствуешь эмоции клиента и отражаешь их
- Адаптируешься к его настроению полностью
- Помнишь все детали разговора
- Поддерживаешь именно в том стиле, который нужен

ОТВЕТ ДОЛЖЕН БЫТЬ:
💙 Максимально эмпатичным с учетом настроения
🤗 Поддерживающим именно в том стиле, который нужен клиенту
💡 Содержащим мягкие, но точные рекомендации
🔄 Учитывающим весь контекст разговора

СТИЛЬ: Очень теплый, понимающий, адаптивный к настроению, помнящий все. 150-300 слов.
""",
                description="Максимальная эмпатия с адаптацией под настроение пользователя"
            )
        ]
        
        # Сохраняем промпты в базу данных
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for prompt in default_prompts:
            cursor.execute('''
                INSERT OR REPLACE INTO prompt_variants 
                (id, type, name, template, description, active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                prompt.id, 
                prompt.type.value, 
                prompt.name, 
                prompt.template, 
                prompt.description, 
                prompt.active
            ))
        
        conn.commit()
        conn.close()

    def get_prompt_for_user(self, user_id: int, prompt_type: PromptType) -> Tuple[str, str]:
        """Получить промпт для пользователя (с учетом A/B тестирования)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже назначенный вариант для этого пользователя
        cursor.execute('''
            SELECT variant_id FROM user_variant_assignments 
            WHERE user_id = ? AND prompt_type = ?
        ''', (user_id, prompt_type.value))
        
        result = cursor.fetchone()
        
        if result:
            variant_id = result[0]
        else:
            # Назначаем случайный активный вариант
            cursor.execute('''
                SELECT id FROM prompt_variants 
                WHERE type = ? AND active = TRUE
            ''', (prompt_type.value,))
            
            variants = cursor.fetchall()
            if not variants:
                conn.close()
                return "", "default"
            
            variant_id = random.choice(variants)[0]
            
            # Сохраняем назначение
            cursor.execute('''
                INSERT OR REPLACE INTO user_variant_assignments 
                (user_id, prompt_type, variant_id)
                VALUES (?, ?, ?)
            ''', (user_id, prompt_type.value, variant_id))
            
            conn.commit()
        
        # Получаем шаблон промпта
        cursor.execute('''
            SELECT template FROM prompt_variants WHERE id = ?
        ''', (variant_id,))
        
        template_result = cursor.fetchone()
        template = template_result[0] if template_result else ""
        
        conn.close()
        return template, variant_id

    def record_test_result(
        self, 
        user_id: int, 
        prompt_variant_id: str, 
        prompt_type: PromptType,
        user_feedback: Optional[float] = None,
        response_quality: Optional[float] = None,
        user_engagement: Optional[float] = None,
        conversion: bool = False
    ):
        """Записать результат A/B теста"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ab_test_results 
            (user_id, prompt_variant_id, prompt_type, user_feedback, 
             response_quality, user_engagement, conversion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, prompt_variant_id, prompt_type.value,
            user_feedback, response_quality, user_engagement, conversion
        ))
        
        conn.commit()
        conn.close()

    def get_test_statistics(self, prompt_type: Optional[PromptType] = None) -> Dict:
        """Получить статистику A/B тестов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Базовый запрос
        base_query = '''
            SELECT 
                r.prompt_variant_id,
                p.name,
                COUNT(*) as total_uses,
                AVG(r.user_feedback) as avg_feedback,
                AVG(r.response_quality) as avg_quality,
                AVG(r.user_engagement) as avg_engagement,
                SUM(CASE WHEN r.conversion = 1 THEN 1 ELSE 0 END) as conversions,
                CAST(SUM(CASE WHEN r.conversion = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as conversion_rate
            FROM ab_test_results r
            JOIN prompt_variants p ON r.prompt_variant_id = p.id
        '''
        
        if prompt_type:
            cursor.execute(base_query + ' WHERE r.prompt_type = ? GROUP BY r.prompt_variant_id', 
                         (prompt_type.value,))
        else:
            cursor.execute(base_query + ' GROUP BY r.prompt_variant_id')
        
        results = cursor.fetchall()
        
        statistics = {}
        for row in results:
            variant_id = row[0]
            statistics[variant_id] = {
                'name': row[1],
                'total_uses': row[2],
                'avg_feedback': row[3] or 0,
                'avg_quality': row[4] or 0,
                'avg_engagement': row[5] or 0,
                'conversions': row[6],
                'conversion_rate': row[7] or 0
            }
        
        conn.close()
        return statistics

    def get_winning_variant(self, prompt_type: PromptType) -> Optional[str]:
        """Определить лучший вариант промпта на основе метрик"""
        stats = self.get_test_statistics(prompt_type)
        
        if not stats:
            return None
        
        # Составной скор: конверсия (40%) + качество (30%) + фидбек (30%)
        best_variant = None
        best_score = -1
        
        for variant_id, data in stats.items():
            if data['total_uses'] < 10:  # Минимум использований для статистической значимости
                continue
                
            score = (
                data['conversion_rate'] * 0.4 +
                (data['avg_quality'] / 5.0) * 0.3 +
                (data['avg_feedback'] / 5.0) * 0.3
            )
            
            if score > best_score:
                best_score = score
                best_variant = variant_id
        
        return best_variant

    def evaluate_response_quality(self, user_message: str, ai_response: str) -> float:
        """Автоматическая оценка качества ответа ИИ (упрощенная)"""
        try:
            # Простые метрики качества
            score = 0.5  # базовый скор
            
            # Длина ответа (не слишком короткий, не слишком длинный)
            response_length = len(ai_response.split())
            if 50 <= response_length <= 400:
                score += 0.1
            
            # Наличие эмоциональных маркеров
            emotional_markers = ['💙', '🤗', '💡', '🎯', '🧠', '💼', '🎓', '⚠️']
            if any(marker in ai_response for marker in emotional_markers):
                score += 0.1
            
            # Структурированность ответа
            if any(marker in ai_response for marker in ['**', '•', '-', '1.', '2.']):
                score += 0.1
            
            # Персонализация (обращение к пользователю)
            personal_words = ['вы', 'ваш', 'ваша', 'вам', 'вас']
            if any(word in ai_response.lower() for word in personal_words):
                score += 0.1
            
            # Практичность (конкретные рекомендации)
            practical_words = ['рекомендую', 'советую', 'попробуйте', 'можете', 'стоит']
            if any(word in ai_response.lower() for word in practical_words):
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error evaluating response quality: {e}")
            return 0.5

def get_ab_testing_manager(db_path: str = 'psychoanalyst.db') -> PromptABTesting:
    """Фабричная функция для получения менеджера A/B тестирования"""
    return PromptABTesting(db_path)

# Пример использования
if __name__ == "__main__":
    ab_manager = get_ab_testing_manager()
    
    # Получаем промпт для пользователя
    template, variant_id = ab_manager.get_prompt_for_user(12345, PromptType.EXPRESS_ANALYSIS)
    print(f"Назначен вариант: {variant_id}")
    
    # Записываем результат теста
    ab_manager.record_test_result(
        user_id=12345,
        prompt_variant_id=variant_id,
        prompt_type=PromptType.EXPRESS_ANALYSIS,
        user_feedback=4.5,
        response_quality=0.8,
        conversion=True
    )
    
    # Получаем статистику
    stats = ab_manager.get_test_statistics()
    for variant, data in stats.items():
        print(f"\nВариант {variant}:")
        print(f"  Использований: {data['total_uses']}")
        print(f"  Конверсия: {data['conversion_rate']:.2%}")
        print(f"  Средняя оценка: {data['avg_feedback']:.1f}/5")