"""
Система машинного обучения для HR-психоаналитического бота
Реализует современные техники самообучения ИИ
"""

import json
import sqlite3
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)

@dataclass
class LearningMetrics:
    """Метрики обучения"""
    user_satisfaction: float  # 0.0 - 1.0
    response_relevance: float  # 0.0 - 1.0
    engagement_score: float  # 0.0 - 1.0
    conversion_rate: float  # 0.0 - 1.0
    session_duration: float  # секунды
    message_count: int
    timestamp: datetime

@dataclass
class UserProfile:
    """Профиль пользователя для персонализации"""
    user_id: int
    preferred_style: str  # formal, casual, supportive, analytical
    communication_patterns: Dict[str, float]  # паттерны общения
    psychological_traits: Dict[str, float]  # психологические черты
    interests: List[str]  # интересы и темы
    last_updated: datetime

@dataclass
class LearningInsight:
    """Инсайт для улучшения бота"""
    insight_type: str  # prompt_improvement, style_adaptation, topic_expansion
    description: str
    confidence: float
    suggested_action: str
    metrics_impact: Dict[str, float]

class MachineLearningSystem:
    """Система машинного обучения для бота"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.user_profiles = {}
        self.learning_insights = []
        self.init_database()
        self.load_user_profiles()
    
    def init_database(self):
        """Инициализация таблиц для машинного обучения"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица метрик обучения
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                user_satisfaction REAL,
                response_relevance REAL,
                engagement_score REAL,
                conversion_rate REAL,
                session_duration REAL,
                message_count INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица профилей пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                preferred_style TEXT,
                communication_patterns TEXT,  -- JSON
                psychological_traits TEXT,    -- JSON
                interests TEXT,               -- JSON
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица инсайтов обучения
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence REAL NOT NULL,
                suggested_action TEXT NOT NULL,
                metrics_impact TEXT,          -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                implemented BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Таблица обратной связи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL,  -- rating, text, behavior
                feedback_data TEXT,           -- JSON
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_user_profiles(self):
        """Загрузка профилей пользователей из БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_profiles')
        rows = cursor.fetchall()
        
        for row in rows:
            user_id, style, patterns_json, traits_json, interests_json, last_updated = row
            
            profile = UserProfile(
                user_id=user_id,
                preferred_style=style or 'balanced',
                communication_patterns=json.loads(patterns_json or '{}'),
                psychological_traits=json.loads(traits_json or '{}'),
                interests=json.loads(interests_json or '[]'),
                last_updated=datetime.fromisoformat(last_updated) if last_updated else datetime.now()
            )
            
            self.user_profiles[user_id] = profile
        
        conn.close()
    
    def analyze_user_message(self, user_id: int, message: str, context: List[str] = None) -> Dict[str, Any]:
        """Анализ сообщения пользователя для обучения"""
        analysis = {
            'sentiment': self._analyze_sentiment(message),
            'topics': self._extract_topics(message),
            'style_preferences': self._analyze_style_preferences(message),
            'psychological_indicators': self._extract_psychological_indicators(message),
            'communication_patterns': self._analyze_communication_patterns(message, context)
        }
        
        # Обновляем профиль пользователя
        self._update_user_profile(user_id, analysis)
        
        return analysis
    
    def generate_adaptive_prompt(self, user_id: int, base_prompt: str, prompt_type: str) -> str:
        """Генерация адаптивного промпта на основе профиля пользователя"""
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            return base_prompt
        
        # Адаптируем промпт под стиль пользователя
        adaptations = []
        
        # Стиль общения
        if profile.preferred_style == 'formal':
            adaptations.append("Используй формальный, профессиональный стиль общения.")
        elif profile.preferred_style == 'casual':
            adaptations.append("Используй дружелюбный, неформальный стиль общения.")
        elif profile.preferred_style == 'supportive':
            adaptations.append("Делай акцент на поддержке и понимании.")
        elif profile.preferred_style == 'analytical':
            adaptations.append("Предоставляй детальный анализ и структурированные ответы.")
        
        # Психологические особенности
        if profile.psychological_traits.get('high_anxiety', 0) > 0.7:
            adaptations.append("Будь особенно деликатным и успокаивающим.")
        
        if profile.psychological_traits.get('high_ambition', 0) > 0.7:
            adaptations.append("Фокусируйся на мотивации и достижениях.")
        
        # Интересы пользователя
        if profile.interests:
            interests_text = ", ".join(profile.interests[:3])  # Топ-3 интереса
            adaptations.append(f"Учитывай интересы пользователя: {interests_text}.")
        
        # Объединяем адаптации с базовым промптом
        if adaptations:
            adapted_prompt = f"{base_prompt}\n\nДОПОЛНИТЕЛЬНЫЕ ИНСТРУКЦИИ:\n" + "\n".join(adaptations)
            return adapted_prompt
        
        return base_prompt
    
    def record_interaction(self, user_id: int, session_id: str, user_message: str, 
                          ai_response: str, metrics: LearningMetrics):
        """Запись взаимодействия для обучения"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Сохраняем метрики
        cursor.execute('''
            INSERT INTO learning_metrics 
            (user_id, session_id, user_satisfaction, response_relevance, 
             engagement_score, conversion_rate, session_duration, message_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, session_id, metrics.user_satisfaction, metrics.response_relevance,
            metrics.engagement_score, metrics.conversion_rate, 
            metrics.session_duration, metrics.message_count
        ))
        
        # Анализируем взаимодействие
        analysis = self.analyze_user_message(user_id, user_message)
        
        # Генерируем инсайты
        insights = self._generate_learning_insights(user_id, analysis, metrics)
        
        for insight in insights:
            self._save_learning_insight(insight, cursor)
        
        conn.commit()
        conn.close()
        
        # Обновляем профиль пользователя в памяти
        self._update_user_profile(user_id, analysis)
    
    def collect_feedback(self, user_id: int, session_id: str, feedback_type: str, 
                        feedback_data: Dict[str, Any]):
        """Сбор обратной связи от пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_feedback 
            (user_id, session_id, feedback_type, feedback_data)
            VALUES (?, ?, ?, ?)
        ''', (user_id, session_id, feedback_type, json.dumps(feedback_data)))
        
        conn.commit()
        conn.close()
        
        # Анализируем обратную связь для обучения
        self._analyze_feedback(user_id, feedback_type, feedback_data)
    
    def get_learning_recommendations(self) -> List[LearningInsight]:
        """Получение рекомендаций по улучшению бота"""
        # Анализируем данные за последние 7 дней
        recent_insights = self._analyze_recent_performance()
        
        # Генерируем новые инсайты
        new_insights = self._generate_performance_insights(recent_insights)
        
        return new_insights
    
    def _analyze_sentiment(self, text: str) -> str:
        """Анализ настроения текста"""
        positive_words = ['хорошо', 'отлично', 'спасибо', 'понравилось', 'помогло']
        negative_words = ['плохо', 'не нравится', 'не помогло', 'не понял', 'плохо']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _extract_topics(self, text: str) -> List[str]:
        """Извлечение тем из текста"""
        topics = []
        
        # Психологические темы
        psych_topics = {
            'стресс': ['стресс', 'напряжение', 'нервы'],
            'отношения': ['отношения', 'семья', 'друзья', 'любовь'],
            'карьера': ['работа', 'карьера', 'профессия', 'учеба'],
            'эмоции': ['эмоции', 'чувства', 'настроение', 'переживания']
        }
        
        text_lower = text.lower()
        for topic, keywords in psych_topics.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _analyze_style_preferences(self, text: str) -> str:
        """Анализ предпочтений стиля общения"""
        text_lower = text.lower()
        
        # Формальный стиль
        formal_indicators = ['пожалуйста', 'спасибо', 'извините', 'благодарю']
        formal_score = sum(1 for indicator in formal_indicators if indicator in text_lower)
        
        # Неформальный стиль
        casual_indicators = ['привет', 'спс', 'ок', 'давай', 'круто']
        casual_score = sum(1 for indicator in casual_indicators if indicator in text_lower)
        
        # Поддерживающий стиль
        supportive_indicators = ['помоги', 'поддержка', 'трудно', 'сложно']
        supportive_score = sum(1 for indicator in supportive_indicators if indicator in text_lower)
        
        # Аналитический стиль
        analytical_indicators = ['анализ', 'данные', 'статистика', 'исследование']
        analytical_score = sum(1 for indicator in analytical_indicators if indicator in text_lower)
        
        scores = {
            'formal': formal_score,
            'casual': casual_score,
            'supportive': supportive_score,
            'analytical': analytical_score
        }
        
        return max(scores, key=scores.get)
    
    def _extract_psychological_indicators(self, text: str) -> Dict[str, float]:
        """Извлечение психологических индикаторов"""
        indicators = {
            'anxiety': 0.0,
            'depression': 0.0,
            'ambition': 0.0,
            'introversion': 0.0,
            'openness': 0.0
        }
        
        text_lower = text.lower()
        
        # Тревожность
        anxiety_words = ['тревога', 'беспокойство', 'волнение', 'страх', 'нервы']
        anxiety_score = sum(1 for word in anxiety_words if word in text_lower) / len(text.split())
        indicators['anxiety'] = min(anxiety_score * 5, 1.0)
        
        # Депрессия
        depression_words = ['грусть', 'печаль', 'уныние', 'апатия', 'безразличие']
        depression_score = sum(1 for word in depression_words if word in text_lower) / len(text.split())
        indicators['depression'] = min(depression_score * 5, 1.0)
        
        # Амбициозность
        ambition_words = ['цель', 'мечта', 'планы', 'успех', 'достижение']
        ambition_score = sum(1 for word in ambition_words if word in text_lower) / len(text.split())
        indicators['ambition'] = min(ambition_score * 5, 1.0)
        
        return indicators
    
    def _analyze_communication_patterns(self, message: str, context: List[str] = None) -> Dict[str, float]:
        """Анализ паттернов общения"""
        patterns = {
            'message_length': len(message.split()),
            'question_frequency': message.count('?') / max(len(message.split()), 1),
            'exclamation_frequency': message.count('!') / max(len(message.split()), 1),
            'emotion_markers': len(re.findall(r'[😀-🙏]', message)) / max(len(message.split()), 1)
        }
        
        # Анализ последовательности сообщений
        if context and len(context) > 1:
            patterns['topic_consistency'] = self._calculate_topic_consistency(context)
            patterns['response_time_pattern'] = self._analyze_response_patterns(context)
        
        return patterns
    
    def _calculate_topic_consistency(self, messages: List[str]) -> float:
        """Расчет консистентности тем в диалоге"""
        topics_per_message = [self._extract_topics(msg) for msg in messages]
        
        if not topics_per_message:
            return 0.0
        
        # Простой алгоритм: считаем пересечения тем между соседними сообщениями
        consistency_score = 0.0
        for i in range(1, len(topics_per_message)):
            prev_topics = set(topics_per_message[i-1])
            curr_topics = set(topics_per_message[i])
            
            if prev_topics and curr_topics:
                intersection = len(prev_topics & curr_topics)
                union = len(prev_topics | curr_topics)
                consistency_score += intersection / union if union > 0 else 0
        
        return consistency_score / max(len(topics_per_message) - 1, 1)
    
    def _analyze_response_patterns(self, messages: List[str]) -> float:
        """Анализ паттернов ответов"""
        # Простой анализ: средняя длина сообщений
        lengths = [len(msg.split()) for msg in messages]
        return np.mean(lengths) if lengths else 0
    
    def _update_user_profile(self, user_id: int, analysis: Dict[str, Any]):
        """Обновление профиля пользователя"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(
                user_id=user_id,
                preferred_style='balanced',
                communication_patterns={},
                psychological_traits={},
                interests=[],
                last_updated=datetime.now()
            )
        
        profile = self.user_profiles[user_id]
        
        # Обновляем стиль общения (экспоненциальное сглаживание)
        new_style = analysis['style_preferences']
        if new_style != profile.preferred_style:
            # Простая логика смены стиля
            profile.preferred_style = new_style
        
        # Обновляем психологические черты
        for trait, value in analysis['psychological_indicators'].items():
            if trait in profile.psychological_traits:
                # Экспоненциальное сглаживание
                profile.psychological_traits[trait] = 0.7 * profile.psychological_traits[trait] + 0.3 * value
            else:
                profile.psychological_traits[trait] = value
        
        # Обновляем интересы
        new_topics = analysis['topics']
        for topic in new_topics:
            if topic not in profile.interests:
                profile.interests.append(topic)
        
        # Ограничиваем количество интересов
        if len(profile.interests) > 10:
            profile.interests = profile.interests[-10:]
        
        # Обновляем паттерны общения
        for pattern, value in analysis['communication_patterns'].items():
            profile.communication_patterns[pattern] = value
        
        profile.last_updated = datetime.now()
        
        # Сохраняем в БД
        self._save_user_profile(profile)
    
    def _save_user_profile(self, profile: UserProfile):
        """Сохранение профиля пользователя в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles 
            (user_id, preferred_style, communication_patterns, psychological_traits, interests, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            profile.user_id,
            profile.preferred_style,
            json.dumps(profile.communication_patterns),
            json.dumps(profile.psychological_traits),
            json.dumps(profile.interests),
            profile.last_updated.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_learning_insights(self, user_id: int, analysis: Dict[str, Any], 
                                   metrics: LearningMetrics) -> List[LearningInsight]:
        """Генерация инсайтов для обучения"""
        insights = []
        
        # Низкая удовлетворенность пользователя
        if metrics.user_satisfaction < 0.5:
            insights.append(LearningInsight(
                insight_type='user_satisfaction',
                description=f'Низкая удовлетворенность пользователя {user_id}',
                confidence=0.8,
                suggested_action='Пересмотреть подход к этому типу пользователей',
                metrics_impact={'user_satisfaction': -0.2}
            ))
        
        # Низкая релевантность ответов
        if metrics.response_relevance < 0.6:
            insights.append(LearningInsight(
                insight_type='response_relevance',
                description='Ответы недостаточно релевантны',
                confidence=0.7,
                suggested_action='Улучшить анализ контекста и тематики',
                metrics_impact={'response_relevance': -0.15}
            ))
        
        # Высокая тревожность пользователя
        if analysis['psychological_indicators'].get('anxiety', 0) > 0.7:
            insights.append(LearningInsight(
                insight_type='emotional_support',
                description=f'Пользователь {user_id} показывает высокий уровень тревожности',
                confidence=0.9,
                suggested_action='Усилить эмоциональную поддержку в промптах',
                metrics_impact={'engagement_score': 0.1}
            ))
        
        return insights
    
    def _save_learning_insight(self, insight: LearningInsight, cursor):
        """Сохранение инсайта в БД"""
        cursor.execute('''
            INSERT INTO learning_insights 
            (insight_type, description, confidence, suggested_action, metrics_impact)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            insight.insight_type,
            insight.description,
            insight.confidence,
            insight.suggested_action,
            json.dumps(insight.metrics_impact)
        ))
    
    def _analyze_feedback(self, user_id: int, feedback_type: str, feedback_data: Dict[str, Any]):
        """Анализ обратной связи"""
        if feedback_type == 'rating' and 'score' in feedback_data:
            score = feedback_data['score']
            
            # Если оценка низкая, генерируем инсайт
            if score < 3:
                insight = LearningInsight(
                    insight_type='user_feedback',
                    description=f'Пользователь {user_id} дал низкую оценку: {score}/5',
                    confidence=0.9,
                    suggested_action='Проанализировать причины недовольства',
                    metrics_impact={'user_satisfaction': -0.3}
                )
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                self._save_learning_insight(insight, cursor)
                conn.commit()
                conn.close()
    
    def _analyze_recent_performance(self) -> Dict[str, Any]:
        """Анализ производительности за последние дни"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем метрики за последние 7 дней
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        cursor.execute('''
            SELECT 
                AVG(user_satisfaction) as avg_satisfaction,
                AVG(response_relevance) as avg_relevance,
                AVG(engagement_score) as avg_engagement,
                AVG(conversion_rate) as avg_conversion,
                COUNT(*) as total_sessions
            FROM learning_metrics 
            WHERE timestamp > ?
        ''', (week_ago,))
        
        result = cursor.fetchone()
        
        performance = {
            'avg_satisfaction': result[0] or 0,
            'avg_relevance': result[1] or 0,
            'avg_engagement': result[2] or 0,
            'avg_conversion': result[3] or 0,
            'total_sessions': result[4] or 0
        }
        
        conn.close()
        return performance
    
    def _generate_performance_insights(self, performance: Dict[str, Any]) -> List[LearningInsight]:
        """Генерация инсайтов на основе производительности"""
        insights = []
        
        # Анализ общей удовлетворенности
        if performance['avg_satisfaction'] < 0.6:
            insights.append(LearningInsight(
                insight_type='overall_performance',
                description=f'Общая удовлетворенность пользователей низкая: {performance["avg_satisfaction"]:.2f}',
                confidence=0.8,
                suggested_action='Провести анализ всех промптов и улучшить качество ответов',
                metrics_impact={'user_satisfaction': -0.1}
            ))
        
        # Анализ конверсии
        if performance['avg_conversion'] < 0.1:
            insights.append(LearningInsight(
                insight_type='conversion',
                description=f'Низкая конверсия в платные услуги: {performance["avg_conversion"]:.2%}',
                confidence=0.7,
                suggested_action='Улучшить мотивацию к покупке полного анализа',
                metrics_impact={'conversion_rate': -0.05}
            ))
        
        return insights
    
    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Получение профиля пользователя"""
        return self.user_profiles.get(user_id)
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Получение статистики обучения"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM learning_metrics')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM learning_metrics')
        unique_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM learning_insights WHERE implemented = FALSE')
        pending_insights = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_interactions': total_interactions,
            'unique_users': unique_users,
            'active_profiles': len(self.user_profiles),
            'pending_insights': pending_insights
        }

def get_ml_system(db_path: str = 'psychoanalyst.db') -> MachineLearningSystem:
    """Фабричная функция для получения системы машинного обучения"""
    return MachineLearningSystem(db_path)

# Пример использования
if __name__ == "__main__":
    ml_system = get_ml_system()
    
    # Анализ сообщения пользователя
    analysis = ml_system.analyze_user_message(
        user_id=12345,
        message="Мне очень грустно и тревожно из-за работы",
        context=["Привет", "Как дела?"]
    )
    
    print("Анализ сообщения:")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    
    # Генерация адаптивного промпта
    adaptive_prompt = ml_system.generate_adaptive_prompt(
        user_id=12345,
        base_prompt="Ты психолог. Помоги пользователю.",
        prompt_type="psychology_consultation"
    )
    
    print("\nАдаптивный промпт:")
    print(adaptive_prompt)
    
    # Статистика
    stats = ml_system.get_learning_statistics()
    print("\nСтатистика обучения:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))