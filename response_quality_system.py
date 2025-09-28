"""
Система оценки качества ответов для постоянного улучшения точности бота
"""
import re
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class QualityMetric(Enum):
    """Метрики качества ответов"""
    RELEVANCE = "relevance"  # Релевантность теме
    COMPLETENESS = "completeness"  # Полнота ответа
    EMPATHY = "empathy"  # Эмпатичность
    PROFESSIONALISM = "professionalism"  # Профессионализм
    CLARITY = "clarity"  # Ясность изложения
    ACTIONABILITY = "actionability"  # Практичность советов

@dataclass
class QualityScore:
    """Оценка качества ответа"""
    overall_score: float  # 0.0-1.0
    metrics: Dict[QualityMetric, float]
    feedback: str
    suggestions: List[str]
    timestamp: datetime

class ResponseQualityAnalyzer:
    """Анализатор качества ответов"""
    
    def __init__(self, db_path: str = 'quality.db'):
        self.db_path = db_path
        self.init_database()
        self._load_quality_patterns()
    
    def init_database(self):
        """Инициализация базы данных для качества"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quality_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                response_id TEXT NOT NULL,
                overall_score REAL NOT NULL,
                metrics TEXT NOT NULL,
                feedback TEXT,
                suggestions TEXT,
                user_input TEXT,
                bot_response TEXT,
                context_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quality_patterns (
                pattern_type TEXT NOT NULL,
                pattern TEXT NOT NULL,
                score_impact REAL NOT NULL,
                metric TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_quality_patterns(self):
        """Загружает паттерны для оценки качества"""
        # Паттерны для анализа качества ответов
        self.quality_patterns = {
            QualityMetric.RELEVANCE: {
                'positive': [
                    r'понимаю.*ситуацию',
                    r'касается.*вопроса',
                    r'относительно.*того',
                    r'в контексте.*разговора'
                ],
                'negative': [
                    r'не понимаю.*о чем',
                    r'не по теме',
                    r'отклонение от.*вопроса'
                ]
            },
            QualityMetric.EMPATHY: {
                'positive': [
                    r'понимаю.*чувства',
                    r'сочувствую',
                    r'поддерживаю',
                    r'это нормально',
                    r'могу представить',
                    r'понимаю.*сложно'
                ],
                'negative': [
                    r'не переживайте',
                    r'это ерунда',
                    r'забудьте об этом',
                    r'не стоит.*волноваться'
                ]
            },
            QualityMetric.PROFESSIONALISM: {
                'positive': [
                    r'с точки зрения.*психологии',
                    r'исследования показывают',
                    r'метод.*анализа',
                    r'профессиональная.*оценка'
                ],
                'negative': [
                    r'я думаю',
                    r'может быть',
                    r'не уверен',
                    r'не знаю.*точно'
                ]
            },
            QualityMetric.CLARITY: {
                'positive': [
                    r'другими словами',
                    r'проще говоря',
                    r'в двух словах',
                    r'кратко.*суть'
                ],
                'negative': [
                    r'сложно.*объяснить',
                    r'запутанно',
                    r'неясно.*выразить'
                ]
            },
            QualityMetric.ACTIONABILITY: {
                'positive': [
                    r'рекомендую.*сделать',
                    r'попробуйте',
                    r'предлагаю.*план',
                    r'конкретные.*шаги'
                ],
                'negative': [
                    r'ничего.*нельзя.*сделать',
                    r'это невозможно',
                    r'сложно.*изменить'
                ]
            }
        }
    
    def analyze_response_quality(self, user_input: str, bot_response: str, 
                               context_data: Dict = None) -> QualityScore:
        """Анализирует качество ответа бота"""
        if context_data is None:
            context_data = {}
        
        metrics = {}
        
        # Анализируем каждую метрику
        for metric in QualityMetric:
            metrics[metric] = self._calculate_metric_score(
                metric, user_input, bot_response, context_data
            )
        
        # Общая оценка как средневзвешенное
        weights = {
            QualityMetric.RELEVANCE: 0.25,
            QualityMetric.EMPATHY: 0.20,
            QualityMetric.PROFESSIONALISM: 0.20,
            QualityMetric.CLARITY: 0.15,
            QualityMetric.ACTIONABILITY: 0.10,
            QualityMetric.COMPLETENESS: 0.10
        }
        
        overall_score = sum(
            metrics[metric] * weights.get(metric, 0.1) 
            for metric in QualityMetric
        )
        
        # Генерируем обратную связь
        feedback, suggestions = self._generate_feedback(metrics, overall_score)
        
        return QualityScore(
            overall_score=overall_score,
            metrics=metrics,
            feedback=feedback,
            suggestions=suggestions,
            timestamp=datetime.now()
        )
    
    def _calculate_metric_score(self, metric: QualityMetric, user_input: str, 
                              bot_response: str, context_data: Dict) -> float:
        """Вычисляет оценку для конкретной метрики"""
        score = 0.5  # Базовая оценка
        
        if metric in self.quality_patterns:
            patterns = self.quality_patterns[metric]
            
            # Проверяем позитивные паттерны
            for pattern in patterns.get('positive', []):
                if re.search(pattern, bot_response, re.IGNORECASE):
                    score += 0.1
            
            # Проверяем негативные паттерны
            for pattern in patterns.get('negative', []):
                if re.search(pattern, bot_response, re.IGNORECASE):
                    score -= 0.1
        
        # Специальная логика для каждой метрики
        if metric == QualityMetric.RELEVANCE:
            score = self._calculate_relevance_score(user_input, bot_response)
        elif metric == QualityMetric.COMPLETENESS:
            score = self._calculate_completeness_score(user_input, bot_response)
        elif metric == QualityMetric.EMPATHY:
            score = self._calculate_empathy_score(user_input, bot_response)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_relevance_score(self, user_input: str, bot_response: str) -> float:
        """Вычисляет релевантность ответа"""
        # Простой анализ ключевых слов
        user_words = set(user_input.lower().split())
        response_words = set(bot_response.lower().split())
        
        # Исключаем служебные слова
        stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'из', 'к', 'у', 'о', 'об'}
        user_words -= stop_words
        response_words -= stop_words
        
        if not user_words:
            return 0.5
        
        # Вычисляем пересечение слов
        common_words = user_words.intersection(response_words)
        relevance_score = len(common_words) / len(user_words)
        
        return min(1.0, relevance_score)
    
    def _calculate_completeness_score(self, user_input: str, bot_response: str) -> float:
        """Вычисляет полноту ответа"""
        # Анализируем длину ответа относительно вопроса
        user_length = len(user_input)
        response_length = len(bot_response)
        
        # Если вопрос короткий, ответ должен быть развернутым
        if user_length < 50 and response_length < 100:
            return 0.3
        elif user_length < 100 and response_length < 200:
            return 0.4
        elif response_length > 300:
            return 0.8
        else:
            return 0.6
    
    def _calculate_empathy_score(self, user_input: str, bot_response: str) -> float:
        """Вычисляет эмпатичность ответа"""
        empathy_keywords = [
            'понимаю', 'сочувствую', 'поддерживаю', 'слышу', 'чувствую',
            'это нормально', 'естественно', 'могу представить', 'понимаю ваши чувства'
        ]
        
        response_lower = bot_response.lower()
        empathy_count = sum(1 for keyword in empathy_keywords if keyword in response_lower)
        
        # Нормализуем к диапазону 0.0-1.0
        return min(1.0, empathy_count * 0.2)
    
    def _generate_feedback(self, metrics: Dict[QualityMetric, float], 
                         overall_score: float) -> Tuple[str, List[str]]:
        """Генерирует обратную связь и предложения"""
        feedback_parts = []
        suggestions = []
        
        # Общая оценка
        if overall_score >= 0.8:
            feedback_parts.append("Отличное качество ответа!")
        elif overall_score >= 0.6:
            feedback_parts.append("Хорошее качество ответа")
        elif overall_score >= 0.4:
            feedback_parts.append("Удовлетворительное качество")
        else:
            feedback_parts.append("Качество требует улучшения")
        
        # Анализ метрик
        weak_metrics = [metric for metric, score in metrics.items() if score < 0.5]
        
        if QualityMetric.RELEVANCE in weak_metrics:
            suggestions.append("Улучшить релевантность ответа теме")
        
        if QualityMetric.EMPATHY in weak_metrics:
            suggestions.append("Добавить больше эмпатии и понимания")
        
        if QualityMetric.PROFESSIONALISM in weak_metrics:
            suggestions.append("Повысить профессионализм ответа")
        
        if QualityMetric.CLARITY in weak_metrics:
            suggestions.append("Сделать ответ более понятным")
        
        if QualityMetric.ACTIONABILITY in weak_metrics:
            suggestions.append("Добавить практические рекомендации")
        
        feedback = " ".join(feedback_parts)
        return feedback, suggestions
    
    def save_quality_score(self, user_id: int, response_id: str, 
                          quality_score: QualityScore, user_input: str, 
                          bot_response: str, context_data: Dict = None):
        """Сохраняет оценку качества в базу данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO quality_scores 
            (user_id, response_id, overall_score, metrics, feedback, suggestions,
             user_input, bot_response, context_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, response_id, quality_score.overall_score,
            json.dumps({metric.value: score for metric, score in quality_score.metrics.items()}),
            quality_score.feedback, json.dumps(quality_score.suggestions),
            user_input, bot_response, json.dumps(context_data or {}),
            quality_score.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def get_quality_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Получает статистику качества ответов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT AVG(overall_score), COUNT(*), MIN(overall_score), MAX(overall_score)
                FROM quality_scores WHERE user_id = ?
            ''', (user_id,))
        else:
            cursor.execute('''
                SELECT AVG(overall_score), COUNT(*), MIN(overall_score), MAX(overall_score)
                FROM quality_scores
            ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or result[1] == 0:
            return {
                'average_score': 0.0,
                'total_responses': 0,
                'min_score': 0.0,
                'max_score': 0.0
            }
        
        return {
            'average_score': result[0] or 0.0,
            'total_responses': result[1],
            'min_score': result[2] or 0.0,
            'max_score': result[3] or 0.0
        }
    
    def get_improvement_suggestions(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Получает предложения по улучшению на основе истории"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT metrics, suggestions, timestamp, overall_score
            FROM quality_scores 
            WHERE user_id = ? AND overall_score < 0.6
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        suggestions = []
        for row in cursor.fetchall():
            metrics = json.loads(row[0])
            suggestion_list = json.loads(row[1])
            
            suggestions.append({
                'metrics': metrics,
                'suggestions': suggestion_list,
                'timestamp': row[2],
                'score': row[3]
            })
        
        conn.close()
        return suggestions

# Глобальный экземпляр анализатора качества
quality_analyzer = ResponseQualityAnalyzer()