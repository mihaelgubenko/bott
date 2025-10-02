"""
Система сбора и обработки обратной связи для HR-психоаналитического бота
Реализует различные методы сбора обратной связи и их анализ
"""

import json
import sqlite3
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """Типы обратной связи"""
    RATING = "rating"  # Оценка 1-5
    THUMBS = "thumbs"  # 👍👎
    TEXT = "text"      # Текстовый отзыв
    BEHAVIOR = "behavior"  # Поведенческие сигналы
    IMPLICIT = "implicit"  # Неявная обратная связь

@dataclass
class FeedbackData:
    """Данные обратной связи"""
    user_id: int
    session_id: str
    feedback_type: FeedbackType
    value: Any  # Значение обратной связи
    context: Dict[str, Any]  # Контекст (сообщение, ответ ИИ, и т.д.)
    timestamp: datetime

@dataclass
class FeedbackInsight:
    """Инсайт на основе обратной связи"""
    insight_type: str
    description: str
    confidence: float
    actionable_items: List[str]
    impact_score: float  # 0.0 - 1.0

class FeedbackSystem:
    """Система сбора и анализа обратной связи"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.feedback_history = []
        self.init_database()
    
    def init_database(self):
        """Инициализация таблиц для обратной связи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица обратной связи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                feedback_value TEXT NOT NULL,
                context TEXT,  -- JSON
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица инсайтов обратной связи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence REAL NOT NULL,
                actionable_items TEXT,  -- JSON
                impact_score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def collect_rating_feedback(self, user_id: int, session_id: str, rating: int, 
                               context: Dict[str, Any] = None) -> bool:
        """Сбор рейтинговой обратной связи (1-5)"""
        if not (1 <= rating <= 5):
            logger.warning(f"Invalid rating {rating} from user {user_id}")
            return False
        
        feedback = FeedbackData(
            user_id=user_id,
            session_id=session_id,
            feedback_type=FeedbackType.RATING,
            value=rating,
            context=context or {},
            timestamp=datetime.now()
        )
        
        return self._save_feedback(feedback)
    
    def collect_thumbs_feedback(self, user_id: int, session_id: str, is_positive: bool,
                               context: Dict[str, Any] = None) -> bool:
        """Сбор обратной связи через лайки/дизлайки"""
        feedback = FeedbackData(
            user_id=user_id,
            session_id=session_id,
            feedback_type=FeedbackType.THUMBS,
            value=1 if is_positive else 0,
            context=context or {},
            timestamp=datetime.now()
        )
        
        return self._save_feedback(feedback)
    
    def collect_text_feedback(self, user_id: int, session_id: str, text: str,
                             context: Dict[str, Any] = None) -> bool:
        """Сбор текстовой обратной связи"""
        if not text or len(text.strip()) < 3:
            return False
        
        feedback = FeedbackData(
            user_id=user_id,
            session_id=session_id,
            feedback_type=FeedbackType.TEXT,
            value=text.strip(),
            context=context or {},
            timestamp=datetime.now()
        )
        
        return self._save_feedback(feedback)
    
    def collect_behavioral_feedback(self, user_id: int, session_id: str, 
                                   behavior_type: str, behavior_data: Dict[str, Any],
                                   context: Dict[str, Any] = None) -> bool:
        """Сбор поведенческой обратной связи"""
        feedback = FeedbackData(
            user_id=user_id,
            session_id=session_id,
            feedback_type=FeedbackType.BEHAVIOR,
            value={
                'behavior_type': behavior_type,
                'behavior_data': behavior_data
            },
            context=context or {},
            timestamp=datetime.now()
        )
        
        return self._save_feedback(feedback)
    
    def collect_implicit_feedback(self, user_id: int, session_id: str, 
                                 user_message: str, ai_response: str,
                                 session_metrics: Dict[str, Any]) -> bool:
        """Сбор неявной обратной связи из поведения пользователя"""
        
        # Анализируем поведенческие сигналы
        implicit_signals = self._analyze_implicit_signals(
            user_message, ai_response, session_metrics
        )
        
        if not implicit_signals:
            return False
        
        feedback = FeedbackData(
            user_id=user_id,
            session_id=session_id,
            feedback_type=FeedbackType.IMPLICIT,
            value=implicit_signals,
            context={
                'user_message': user_message,
                'ai_response': ai_response,
                'session_metrics': session_metrics
            },
            timestamp=datetime.now()
        )
        
        return self._save_feedback(feedback)
    
    def _analyze_implicit_signals(self, user_message: str, ai_response: str, 
                                 session_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ неявных сигналов обратной связи"""
        signals = {}
        
        # Анализ длины ответа пользователя (показатель вовлеченности)
        message_length = len(user_message.split())
        signals['engagement_level'] = min(message_length / 50.0, 1.0)  # Нормализуем
        
        # Анализ времени ответа (если доступно)
        if 'response_time' in session_metrics:
            response_time = session_metrics['response_time']
            # Быстрый ответ = высокое вовлечение
            signals['response_speed'] = max(0, 1.0 - response_time / 300.0)  # 5 минут = 0
        
        # Анализ эмоциональной окраски
        sentiment = self._analyze_message_sentiment(user_message)
        signals['sentiment'] = sentiment
        
        # Анализ повторных обращений к теме
        if 'previous_messages' in session_metrics:
            topic_consistency = self._analyze_topic_consistency(
                session_metrics['previous_messages'] + [user_message]
            )
            signals['topic_engagement'] = topic_consistency
        
        # Анализ вопросов (показатель интереса)
        question_count = user_message.count('?')
        signals['curiosity_level'] = min(question_count / 3.0, 1.0)
        
        # Анализ благодарности (показатель удовлетворенности)
        gratitude_words = ['спасибо', 'благодарю', 'отлично', 'понравилось', 'помогло']
        has_gratitude = any(word in user_message.lower() for word in gratitude_words)
        signals['satisfaction_positive'] = 1.0 if has_gratitude else 0.0
        
        # Анализ негативных сигналов
        negative_words = ['плохо', 'не нравится', 'не помогло', 'не понял', 'не то']
        has_negative = any(word in user_message.lower() for word in negative_words)
        signals['satisfaction_negative'] = 1.0 if has_negative else 0.0
        
        return signals
    
    def _analyze_message_sentiment(self, message: str) -> str:
        """Простой анализ настроения сообщения"""
        positive_words = ['хорошо', 'отлично', 'спасибо', 'понравилось', 'помогло', 'классно']
        negative_words = ['плохо', 'не нравится', 'не помогло', 'грустно', 'плохо']
        
        message_lower = message.lower()
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _analyze_topic_consistency(self, messages: List[str]) -> float:
        """Анализ консистентности тем в диалоге"""
        if len(messages) < 2:
            return 0.5
        
        # Извлекаем ключевые слова из каждого сообщения
        keywords_per_message = []
        for msg in messages:
            # Простое извлечение ключевых слов (слова длиннее 4 символов)
            words = re.findall(r'\b\w{4,}\b', msg.lower())
            keywords_per_message.append(set(words))
        
        # Считаем пересечения между соседними сообщениями
        consistency_scores = []
        for i in range(1, len(keywords_per_message)):
            prev_keywords = keywords_per_message[i-1]
            curr_keywords = keywords_per_message[i]
            
            if prev_keywords and curr_keywords:
                intersection = len(prev_keywords & curr_keywords)
                union = len(prev_keywords | curr_keywords)
                if union > 0:
                    consistency_scores.append(intersection / union)
        
        return np.mean(consistency_scores) if consistency_scores else 0.5
    
    def _save_feedback(self, feedback: FeedbackData) -> bool:
        """Сохранение обратной связи в БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO feedback_data 
                (user_id, session_id, feedback_type, feedback_value, context)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                feedback.user_id,
                feedback.session_id,
                feedback.feedback_type.value,
                json.dumps(feedback.value),
                json.dumps(feedback.context)
            ))
            
            conn.commit()
            conn.close()
            
            # Анализируем обратную связь для генерации инсайтов
            self._analyze_feedback_for_insights(feedback)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            return False
    
    def _analyze_feedback_for_insights(self, feedback: FeedbackData):
        """Анализ обратной связи для генерации инсайтов"""
        insights = []
        
        # Анализ рейтинговой обратной связи
        if feedback.feedback_type == FeedbackType.RATING:
            rating = feedback.value
            if rating <= 2:
                insights.append(FeedbackInsight(
                    insight_type='low_rating',
                    description=f'Пользователь {feedback.user_id} дал низкую оценку: {rating}/5',
                    confidence=0.9,
                    actionable_items=[
                        'Проанализировать контекст низкой оценки',
                        'Улучшить качество ответов для похожих случаев',
                        'Рассмотреть изменение подхода к этому типу запросов'
                    ],
                    impact_score=0.8
                ))
            elif rating >= 4:
                insights.append(FeedbackInsight(
                    insight_type='high_rating',
                    description=f'Пользователь {feedback.user_id} дал высокую оценку: {rating}/5',
                    confidence=0.8,
                    actionable_items=[
                        'Сохранить успешный подход',
                        'Применить к похожим случаям',
                        'Документировать лучшие практики'
                    ],
                    impact_score=0.6
                ))
        
        # Анализ текстовой обратной связи
        elif feedback.feedback_type == FeedbackType.TEXT:
            text = feedback.value.lower()
            
            # Поиск конкретных проблем
            if any(word in text for word in ['не понял', 'не понятно', 'запутался']):
                insights.append(FeedbackInsight(
                    insight_type='clarity_issue',
                    description=f'Проблема с ясностью ответов у пользователя {feedback.user_id}',
                    confidence=0.8,
                    actionable_items=[
                        'Упростить формулировки',
                        'Добавить больше примеров',
                        'Структурировать ответы лучше'
                    ],
                    impact_score=0.7
                ))
            
            # Поиск положительных отзывов
            elif any(word in text for word in ['понравилось', 'помогло', 'спасибо', 'отлично']):
                insights.append(FeedbackInsight(
                    insight_type='positive_feedback',
                    description=f'Положительный отзыв от пользователя {feedback.user_id}',
                    confidence=0.9,
                    actionable_items=[
                        'Сохранить успешный подход',
                        'Рекомендовать другим пользователям'
                    ],
                    impact_score=0.5
                ))
        
        # Анализ поведенческой обратной связи
        elif feedback.feedback_type == FeedbackType.BEHAVIOR:
            behavior_data = feedback.value
            
            if behavior_data.get('behavior_type') == 'early_exit':
                insights.append(FeedbackInsight(
                    insight_type='early_exit',
                    description=f'Пользователь {feedback.user_id} завершил сессию раньше времени',
                    confidence=0.7,
                    actionable_items=[
                        'Проанализировать причины раннего выхода',
                        'Улучшить первые сообщения',
                        'Сделать взаимодействие более интересным'
                    ],
                    impact_score=0.8
                ))
        
        # Анализ неявной обратной связи
        elif feedback.feedback_type == FeedbackType.IMPLICIT:
            signals = feedback.value
            
            # Низкий уровень вовлеченности
            if signals.get('engagement_level', 0.5) < 0.3:
                insights.append(FeedbackInsight(
                    insight_type='low_engagement',
                    description=f'Низкий уровень вовлеченности у пользователя {feedback.user_id}',
                    confidence=0.7,
                    actionable_items=[
                        'Сделать вопросы более интересными',
                        'Добавить интерактивные элементы',
                        'Персонализировать подход'
                    ],
                    impact_score=0.6
                ))
            
            # Высокий уровень негатива
            if signals.get('satisfaction_negative', 0) > 0.5:
                insights.append(FeedbackInsight(
                    insight_type='negative_sentiment',
                    description=f'Негативные сигналы от пользователя {feedback.user_id}',
                    confidence=0.8,
                    actionable_items=[
                        'Улучшить эмоциональную поддержку',
                        'Пересмотреть подход к ответам',
                        'Добавить больше эмпатии'
                    ],
                    impact_score=0.9
                ))
        
        # Сохраняем инсайты
        for insight in insights:
            self._save_feedback_insight(insight)
    
    def _save_feedback_insight(self, insight: FeedbackInsight):
        """Сохранение инсайта обратной связи"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO feedback_insights 
                (insight_type, description, confidence, actionable_items, impact_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                insight.insight_type,
                insight.description,
                insight.confidence,
                json.dumps(insight.actionable_items),
                insight.impact_score
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving feedback insight: {e}")
    
    def get_feedback_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Получение статистики обратной связи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Период анализа
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Общая статистика
        cursor.execute('''
            SELECT COUNT(*) FROM feedback_data WHERE timestamp > ?
        ''', (since_date,))
        total_feedback = cursor.fetchone()[0]
        
        # Статистика по типам
        cursor.execute('''
            SELECT feedback_type, COUNT(*) FROM feedback_data 
            WHERE timestamp > ? GROUP BY feedback_type
        ''', (since_date,))
        feedback_by_type = dict(cursor.fetchall())
        
        # Статистика рейтингов
        cursor.execute('''
            SELECT AVG(CAST(feedback_value AS REAL)) FROM feedback_data 
            WHERE feedback_type = 'rating' AND timestamp > ?
        ''', (since_date,))
        avg_rating = cursor.fetchone()[0]
        
        # Статистика лайков/дизлайков
        cursor.execute('''
            SELECT feedback_value, COUNT(*) FROM feedback_data 
            WHERE feedback_type = 'thumbs' AND timestamp > ? GROUP BY feedback_value
        ''', (since_date,))
        thumbs_stats = dict(cursor.fetchall())
        
        # Количество инсайтов
        cursor.execute('''
            SELECT COUNT(*) FROM feedback_insights WHERE created_at > ? AND resolved = FALSE
        ''', (since_date,))
        pending_insights = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'period_days': days,
            'total_feedback': total_feedback,
            'feedback_by_type': feedback_by_type,
            'average_rating': round(avg_rating, 2) if avg_rating else None,
            'thumbs_up': thumbs_stats.get('1', 0),
            'thumbs_down': thumbs_stats.get('0', 0),
            'pending_insights': pending_insights
        }
    
    def get_feedback_insights(self, limit: int = 10) -> List[FeedbackInsight]:
        """Получение инсайтов обратной связи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT insight_type, description, confidence, actionable_items, impact_score
            FROM feedback_insights 
            WHERE resolved = FALSE 
            ORDER BY impact_score DESC, confidence DESC
            LIMIT ?
        ''', (limit,))
        
        insights = []
        for row in cursor.fetchall():
            insight = FeedbackInsight(
                insight_type=row[0],
                description=row[1],
                confidence=row[2],
                actionable_items=json.loads(row[3]),
                impact_score=row[4]
            )
            insights.append(insight)
        
        conn.close()
        return insights
    
    def mark_insight_resolved(self, insight_id: int):
        """Отметить инсайт как решенный"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE feedback_insights SET resolved = TRUE WHERE id = ?
        ''', (insight_id,))
        
        conn.commit()
        conn.close()
    
    def suggest_feedback_prompts(self, user_id: int, session_context: Dict[str, Any]) -> List[str]:
        """Предложение промптов для сбора обратной связи"""
        prompts = []
        
        # Базовые промпты
        base_prompts = [
            "Как вам наш разговор? Оцените от 1 до 5 ⭐",
            "Помог ли я вам? Поставьте 👍 или 👎",
            "Есть ли что-то, что можно улучшить?",
        ]
        
        # Контекстные промпты
        if session_context.get('session_length', 0) > 5:
            prompts.append("Вы уже много общались со мной. Как вам наши разговоры?")
        
        if session_context.get('analysis_completed', False):
            prompts.append("Понравился ли вам анализ? Что можно улучшить?")
        
        if session_context.get('has_questions', False):
            prompts.append("Ответил ли я на ваши вопросы? Что еще интересует?")
        
        # Добавляем базовые промпты
        prompts.extend(base_prompts)
        
        return prompts[:3]  # Возвращаем максимум 3 промпта

def get_feedback_system(db_path: str = 'psychoanalyst.db') -> FeedbackSystem:
    """Фабричная функция для получения системы обратной связи"""
    return FeedbackSystem(db_path)

# Пример использования
if __name__ == "__main__":
    feedback_system = get_feedback_system()
    
    # Сбор различных типов обратной связи
    feedback_system.collect_rating_feedback(
        user_id=12345,
        session_id="session_123",
        rating=4,
        context={'message_type': 'analysis_result'}
    )
    
    feedback_system.collect_thumbs_feedback(
        user_id=12345,
        session_id="session_123",
        is_positive=True
    )
    
    feedback_system.collect_text_feedback(
        user_id=12345,
        session_id="session_123",
        text="Очень понравилось! Спасибо за помощь"
    )
    
    # Неявная обратная связь
    feedback_system.collect_implicit_feedback(
        user_id=12345,
        session_id="session_123",
        user_message="Спасибо, очень помогли! Буду рекомендовать друзьям",
        ai_response="Рад был помочь!",
        session_metrics={
            'response_time': 30,
            'previous_messages': ['Привет', 'Как дела?']
        }
    )
    
    # Получение статистики
    stats = feedback_system.get_feedback_statistics()
    print("Статистика обратной связи:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # Получение инсайтов
    insights = feedback_system.get_feedback_insights()
    print("\nИнсайты:")
    for insight in insights:
        print(f"- {insight.description} (уверенность: {insight.confidence:.2f})")