"""
Система аналитики для отслеживания улучшений HR-психоаналитического бота
Отслеживает метрики, тренды и эффективность самообучения
"""

import json
import sqlite3
import logging
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class LearningMetrics:
    """Метрики обучения"""
    timestamp: datetime
    user_satisfaction: float
    response_quality: float
    engagement_score: float
    conversion_rate: float
    avg_session_duration: float
    total_users: int
    active_users: int

@dataclass
class PerformanceTrend:
    """Тренд производительности"""
    metric_name: str
    values: List[float]
    timestamps: List[datetime]
    trend_direction: str  # 'up', 'down', 'stable'
    trend_strength: float  # 0.0 - 1.0
    significance: float  # статистическая значимость

@dataclass
class LearningInsight:
    """Инсайт для улучшения"""
    insight_id: str
    title: str
    description: str
    impact_score: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    category: str  # 'performance', 'user_behavior', 'system_optimization'
    actionable_items: List[str]
    expected_improvement: float  # ожидаемое улучшение в %
    created_at: datetime

class LearningAnalytics:
    """Система аналитики для отслеживания улучшений"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация таблиц для аналитики"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица ежедневных метрик
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                user_satisfaction REAL,
                response_quality REAL,
                engagement_score REAL,
                conversion_rate REAL,
                avg_session_duration REAL,
                total_users INTEGER,
                active_users INTEGER,
                total_sessions INTEGER,
                ab_test_conversions INTEGER,
                feedback_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        ''')
        
        # Таблица инсайтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                impact_score REAL NOT NULL,
                confidence REAL NOT NULL,
                category TEXT NOT NULL,
                actionable_items TEXT,  -- JSON
                expected_improvement REAL,
                status TEXT DEFAULT 'pending',  -- pending, implementing, completed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                implemented_at TIMESTAMP,
                actual_improvement REAL
            )
        ''')
        
        # Таблица экспериментов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_name TEXT NOT NULL,
                description TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                control_group_size INTEGER,
                test_group_size INTEGER,
                control_metric REAL,
                test_metric REAL,
                improvement REAL,
                significance REAL,
                status TEXT DEFAULT 'running',  -- running, completed, failed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def calculate_daily_metrics(self, date: datetime = None) -> LearningMetrics:
        """Расчет ежедневных метрик"""
        if date is None:
            date = datetime.now().date()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем данные за день
        date_str = date.isoformat()
        
        # Пользовательская удовлетворенность (из обратной связи)
        cursor.execute('''
            SELECT AVG(CAST(feedback_value AS REAL)) 
            FROM feedback_data 
            WHERE feedback_type = 'rating' 
            AND DATE(timestamp) = ?
        ''', (date_str,))
        user_satisfaction = cursor.fetchone()[0] or 0.5
        user_satisfaction = user_satisfaction / 5.0  # Нормализуем к 0-1
        
        # Качество ответов (из A/B тестов)
        cursor.execute('''
            SELECT AVG(response_quality) 
            FROM ab_test_results 
            WHERE DATE(timestamp) = ?
        ''', (date_str,))
        response_quality = cursor.fetchone()[0] or 0.5
        
        # Уровень вовлеченности (средняя длина сессии)
        cursor.execute('''
            SELECT AVG(session_duration), COUNT(*) 
            FROM learning_metrics 
            WHERE DATE(timestamp) = ?
        ''', (date_str,))
        result = cursor.fetchone()
        avg_session_duration = result[0] or 0
        total_sessions = result[1] or 0
        
        # Нормализуем длительность сессии (максимум 30 минут = 1.0)
        engagement_score = min(avg_session_duration / 1800.0, 1.0)
        
        # Конверсия в платные услуги
        cursor.execute('''
            SELECT SUM(CASE WHEN conversion = 1 THEN 1 ELSE 0 END), COUNT(*) 
            FROM ab_test_results 
            WHERE DATE(timestamp) = ?
        ''', (date_str,))
        result = cursor.fetchone()
        conversions = result[0] or 0
        total_users = result[1] or 1
        conversion_rate = conversions / total_users
        
        # Активные пользователи
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) 
            FROM learning_metrics 
            WHERE DATE(timestamp) = ?
        ''', (date_str,))
        active_users = cursor.fetchone()[0] or 0
        
        # Общее количество пользователей
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM learning_metrics')
        total_users = cursor.fetchone()[0] or 0
        
        conn.close()
        
        metrics = LearningMetrics(
            timestamp=datetime.combine(date, datetime.min.time()),
            user_satisfaction=user_satisfaction,
            response_quality=response_quality,
            engagement_score=engagement_score,
            conversion_rate=conversion_rate,
            avg_session_duration=avg_session_duration,
            total_users=total_users,
            active_users=active_users
        )
        
        # Сохраняем метрики
        self._save_daily_metrics(metrics, total_sessions)
        
        return metrics
    
    def _save_daily_metrics(self, metrics: LearningMetrics, total_sessions: int):
        """Сохранение ежедневных метрик"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем количество обратной связи за день
        date_str = metrics.timestamp.date().isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM feedback_data WHERE DATE(timestamp) = ?
        ''', (date_str,))
        feedback_count = cursor.fetchone()[0] or 0
        
        # Получаем количество конверсий A/B тестов
        cursor.execute('''
            SELECT SUM(CASE WHEN conversion = 1 THEN 1 ELSE 0 END) 
            FROM ab_test_results WHERE DATE(timestamp) = ?
        ''', (date_str,))
        ab_test_conversions = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_metrics 
            (date, user_satisfaction, response_quality, engagement_score, 
             conversion_rate, avg_session_duration, total_users, active_users,
             total_sessions, ab_test_conversions, feedback_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            date_str, metrics.user_satisfaction, metrics.response_quality,
            metrics.engagement_score, metrics.conversion_rate,
            metrics.avg_session_duration, metrics.total_users, metrics.active_users,
            total_sessions, ab_test_conversions, feedback_count
        ))
        
        conn.commit()
        conn.close()
    
    def analyze_performance_trends(self, days: int = 30) -> List[PerformanceTrend]:
        """Анализ трендов производительности"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем данные за указанный период
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        
        cursor.execute('''
            SELECT date, user_satisfaction, response_quality, engagement_score, 
                   conversion_rate, avg_session_duration
            FROM daily_metrics 
            WHERE date >= ?
            ORDER BY date
        ''', (start_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return []
        
        # Разделяем данные по метрикам
        dates = [datetime.fromisoformat(row[0]) for row in rows]
        metrics_data = {
            'user_satisfaction': [row[1] for row in rows],
            'response_quality': [row[2] for row in rows],
            'engagement_score': [row[3] for row in rows],
            'conversion_rate': [row[4] for row in rows],
            'avg_session_duration': [row[5] for row in rows]
        }
        
        trends = []
        for metric_name, values in metrics_data.items():
            if len(values) < 2:
                continue
            
            # Рассчитываем тренд
            trend_direction, trend_strength, significance = self._calculate_trend(values)
            
            trend = PerformanceTrend(
                metric_name=metric_name,
                values=values,
                timestamps=dates,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                significance=significance
            )
            
            trends.append(trend)
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> Tuple[str, float, float]:
        """Расчет тренда для метрики"""
        if len(values) < 2:
            return 'stable', 0.0, 0.0
        
        # Простая линейная регрессия
        x = np.arange(len(values))
        y = np.array(values)
        
        # Убираем NaN значения
        mask = ~np.isnan(y)
        if not np.any(mask):
            return 'stable', 0.0, 0.0
        
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 2:
            return 'stable', 0.0, 0.0
        
        # Коэффициент корреляции
        correlation = np.corrcoef(x_clean, y_clean)[0, 1]
        
        if np.isnan(correlation):
            return 'stable', 0.0, 0.0
        
        # Направление тренда
        if correlation > 0.3:
            direction = 'up'
        elif correlation < -0.3:
            direction = 'down'
        else:
            direction = 'stable'
        
        # Сила тренда (абсолютное значение корреляции)
        strength = abs(correlation)
        
        # Значимость (упрощенная оценка)
        significance = min(strength * 2, 1.0)
        
        return direction, strength, significance
    
    def generate_learning_insights(self) -> List[LearningInsight]:
        """Генерация инсайтов для улучшения"""
        insights = []
        
        # Анализируем тренды
        trends = self.analyze_performance_trends(days=7)
        
        for trend in trends:
            if trend.trend_direction == 'down' and trend.significance > 0.5:
                # Негативный тренд
                insight = self._create_negative_trend_insight(trend)
                insights.append(insight)
            elif trend.trend_direction == 'up' and trend.significance > 0.7:
                # Положительный тренд
                insight = self._create_positive_trend_insight(trend)
                insights.append(insight)
        
        # Анализируем пользовательское поведение
        behavior_insights = self._analyze_user_behavior()
        insights.extend(behavior_insights)
        
        # Анализируем эффективность A/B тестов
        ab_insights = self._analyze_ab_test_effectiveness()
        insights.extend(ab_insights)
        
        # Анализируем обратную связь
        feedback_insights = self._analyze_feedback_patterns()
        insights.extend(feedback_insights)
        
        return insights
    
    def _create_negative_trend_insight(self, trend: PerformanceTrend) -> LearningInsight:
        """Создание инсайта для негативного тренда"""
        metric_names = {
            'user_satisfaction': 'удовлетворенности пользователей',
            'response_quality': 'качества ответов',
            'engagement_score': 'вовлеченности пользователей',
            'conversion_rate': 'конверсии в платные услуги',
            'avg_session_duration': 'длительности сессий'
        }
        
        metric_name_ru = metric_names.get(trend.metric_name, trend.metric_name)
        
        return LearningInsight(
            insight_id=f"negative_trend_{trend.metric_name}_{datetime.now().strftime('%Y%m%d')}",
            title=f"Снижение {metric_name_ru}",
            description=f"Обнаружен негативный тренд в метрике {metric_name_ru} за последние 7 дней",
            impact_score=trend.trend_strength,
            confidence=trend.significance,
            category='performance',
            actionable_items=self._get_actionable_items_for_metric(trend.metric_name),
            expected_improvement=15.0,  # Ожидаем улучшение на 15%
            created_at=datetime.now()
        )
    
    def _create_positive_trend_insight(self, trend: PerformanceTrend) -> LearningInsight:
        """Создание инсайта для положительного тренда"""
        metric_names = {
            'user_satisfaction': 'удовлетворенности пользователей',
            'response_quality': 'качества ответов',
            'engagement_score': 'вовлеченности пользователей',
            'conversion_rate': 'конверсии в платные услуги',
            'avg_session_duration': 'длительности сессий'
        }
        
        metric_name_ru = metric_names.get(trend.metric_name, trend.metric_name)
        
        return LearningInsight(
            insight_id=f"positive_trend_{trend.metric_name}_{datetime.now().strftime('%Y%m%d')}",
            title=f"Рост {metric_name_ru}",
            description=f"Обнаружен положительный тренд в метрике {metric_name_ru} за последние 7 дней",
            impact_score=trend.trend_strength,
            confidence=trend.significance,
            category='performance',
            actionable_items=[
                'Продолжать текущую стратегию',
                'Документировать успешные практики',
                'Применить подход к другим метрикам'
            ],
            expected_improvement=5.0,  # Ожидаем дальнейшее улучшение на 5%
            created_at=datetime.now()
        )
    
    def _get_actionable_items_for_metric(self, metric_name: str) -> List[str]:
        """Получение рекомендаций для конкретной метрики"""
        recommendations = {
            'user_satisfaction': [
                'Улучшить качество ответов ИИ',
                'Оптимизировать промпты',
                'Усилить персонализацию',
                'Улучшить обработку жалоб'
            ],
            'response_quality': [
                'Обновить промпты на основе лучших практик',
                'Улучшить анализ контекста',
                'Добавить больше примеров в обучение',
                'Оптимизировать A/B тестирование'
            ],
            'engagement_score': [
                'Сделать диалоги более интерактивными',
                'Добавить интересные вопросы',
                'Улучшить первую встречу с пользователем',
                'Персонализировать подход'
            ],
            'conversion_rate': [
                'Улучшить мотивацию к покупке',
                'Оптимизировать предложения',
                'Добавить социальные доказательства',
                'Улучшить процесс оплаты'
            ],
            'avg_session_duration': [
                'Добавить более интересный контент',
                'Улучшить качество анализа',
                'Сделать вопросы более глубокими',
                'Добавить интерактивные элементы'
            ]
        }
        
        return recommendations.get(metric_name, ['Проанализировать причины снижения'])
    
    def _analyze_user_behavior(self) -> List[LearningInsight]:
        """Анализ поведения пользователей"""
        insights = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Анализ раннего выхода из сессий
        cursor.execute('''
            SELECT COUNT(*) FROM learning_metrics 
            WHERE session_duration < 60 AND message_count < 3
        ''')
        early_exits = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM learning_metrics')
        total_sessions = cursor.fetchone()[0] or 1
        
        early_exit_rate = early_exits / total_sessions
        
        if early_exit_rate > 0.3:  # Более 30% ранних выходов
            insights.append(LearningInsight(
                insight_id=f"early_exit_high_{datetime.now().strftime('%Y%m%d')}",
                title="Высокий процент ранних выходов",
                description=f"{(early_exit_rate*100):.1f}% пользователей завершают сессию раньше времени",
                impact_score=early_exit_rate,
                confidence=0.8,
                category='user_behavior',
                actionable_items=[
                    'Улучшить первые сообщения бота',
                    'Сделать приветствие более интересным',
                    'Добавить интерактивные элементы',
                    'Персонализировать подход с самого начала'
                ],
                expected_improvement=20.0,
                created_at=datetime.now()
            ))
        
        conn.close()
        return insights
    
    def _analyze_ab_test_effectiveness(self) -> List[LearningInsight]:
        """Анализ эффективности A/B тестов"""
        insights = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем статистику A/B тестов
        cursor.execute('''
            SELECT prompt_type, COUNT(*) as total_tests, 
                   AVG(response_quality) as avg_quality,
                   AVG(user_feedback) as avg_feedback
            FROM ab_test_results 
            GROUP BY prompt_type
        ''')
        
        results = cursor.fetchall()
        
        for prompt_type, total_tests, avg_quality, avg_feedback in results:
            if total_tests > 10:  # Достаточно данных для анализа
                # Проверяем, есть ли значительные различия в качестве
                cursor.execute('''
                    SELECT prompt_variant_id, AVG(response_quality) 
                    FROM ab_test_results 
                    WHERE prompt_type = ? 
                    GROUP BY prompt_variant_id
                ''', (prompt_type,))
                
                variant_qualities = cursor.fetchall()
                
                if len(variant_qualities) > 1:
                    qualities = [q[1] for q in variant_qualities if q[1] is not None]
                    if qualities:
                        quality_range = max(qualities) - min(qualities)
                        
                        if quality_range > 0.2:  # Значительное различие
                            insights.append(LearningInsight(
                                insight_id=f"ab_test_variation_{prompt_type}_{datetime.now().strftime('%Y%m%d')}",
                                title=f"Различия в качестве промптов {prompt_type}",
                                description=f"Обнаружены значительные различия в качестве разных вариантов промптов",
                                impact_score=quality_range,
                                confidence=0.7,
                                category='system_optimization',
                                actionable_items=[
                                    'Выбрать лучший вариант промпта',
                                    'Применить лучшие практики ко всем промптам',
                                    'Продолжить тестирование новых вариантов'
                                ],
                                expected_improvement=10.0,
                                created_at=datetime.now()
                            ))
        
        conn.close()
        return insights
    
    def _analyze_feedback_patterns(self) -> List[LearningInsight]:
        """Анализ паттернов обратной связи"""
        insights = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Анализ низких оценок
        cursor.execute('''
            SELECT COUNT(*) FROM feedback_data 
            WHERE feedback_type = 'rating' AND CAST(feedback_value AS REAL) <= 2
        ''')
        low_ratings = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM feedback_data 
            WHERE feedback_type = 'rating'
        ''')
        total_ratings = cursor.fetchone()[0] or 1
        
        low_rating_rate = low_ratings / total_ratings
        
        if low_rating_rate > 0.2:  # Более 20% низких оценок
            insights.append(LearningInsight(
                insight_id=f"low_ratings_high_{datetime.now().strftime('%Y%m%d')}",
                title="Высокий процент низких оценок",
                description=f"{(low_rating_rate*100):.1f}% пользователей дают низкие оценки",
                impact_score=low_rating_rate,
                confidence=0.9,
                category='user_behavior',
                actionable_items=[
                    'Проанализировать причины низких оценок',
                    'Улучшить качество ответов',
                    'Добавить больше персонализации',
                    'Улучшить обработку жалоб'
                ],
                expected_improvement=25.0,
                created_at=datetime.now()
            ))
        
        conn.close()
        return insights
    
    def save_learning_insight(self, insight: LearningInsight):
        """Сохранение инсайта"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO learning_insights 
            (insight_id, title, description, impact_score, confidence, 
             category, actionable_items, expected_improvement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            insight.insight_id,
            insight.title,
            insight.description,
            insight.impact_score,
            insight.confidence,
            insight.category,
            json.dumps(insight.actionable_items),
            insight.expected_improvement
        ))
        
        conn.commit()
        conn.close()
    
    def get_learning_dashboard_data(self) -> Dict[str, Any]:
        """Получение данных для дашборда обучения"""
        
        # Текущие метрики
        current_metrics = self.calculate_daily_metrics()
        
        # Тренды за последние 7 дней
        trends = self.analyze_performance_trends(days=7)
        
        # Активные инсайты
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM learning_insights 
            WHERE status = 'pending'
        ''')
        pending_insights = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM learning_insights 
            WHERE status = 'implementing'
        ''')
        implementing_insights = cursor.fetchone()[0] or 0
        
        # Статистика экспериментов
        cursor.execute('''
            SELECT COUNT(*) FROM learning_experiments 
            WHERE status = 'running'
        ''')
        active_experiments = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Формируем данные для дашборда
        dashboard_data = {
            'current_metrics': asdict(current_metrics),
            'trends': [
                {
                    'metric_name': trend.metric_name,
                    'trend_direction': trend.trend_direction,
                    'trend_strength': trend.trend_strength,
                    'significance': trend.significance
                }
                for trend in trends
            ],
            'insights_summary': {
                'pending_insights': pending_insights,
                'implementing_insights': implementing_insights,
                'total_active_insights': pending_insights + implementing_insights
            },
            'experiments_summary': {
                'active_experiments': active_experiments
            },
            'overall_health_score': self._calculate_overall_health_score(current_metrics, trends)
        }
        
        return dashboard_data
    
    def _calculate_overall_health_score(self, metrics: LearningMetrics, 
                                       trends: List[PerformanceTrend]) -> float:
        """Расчет общего индекса здоровья системы"""
        
        # Базовые метрики (веса)
        base_score = (
            metrics.user_satisfaction * 0.3 +
            metrics.response_quality * 0.25 +
            metrics.engagement_score * 0.2 +
            metrics.conversion_rate * 0.15 +
            (metrics.active_users / max(metrics.total_users, 1)) * 0.1
        )
        
        # Корректировка по трендам
        trend_adjustment = 0.0
        for trend in trends:
            if trend.trend_direction == 'up':
                trend_adjustment += trend.trend_strength * 0.1
            elif trend.trend_direction == 'down':
                trend_adjustment -= trend.trend_strength * 0.1
        
        final_score = base_score + trend_adjustment
        return max(0.0, min(1.0, final_score))  # Ограничиваем от 0 до 1

def get_learning_analytics(db_path: str = 'psychoanalyst.db') -> LearningAnalytics:
    """Фабричная функция для получения системы аналитики"""
    return LearningAnalytics(db_path)

# Пример использования
if __name__ == "__main__":
    analytics = get_learning_analytics()
    
    # Расчет метрик
    metrics = analytics.calculate_daily_metrics()
    print("Ежедневные метрики:")
    print(json.dumps(asdict(metrics), indent=2, ensure_ascii=False, default=str))
    
    # Анализ трендов
    trends = analytics.analyze_performance_trends(days=7)
    print("\nТренды:")
    for trend in trends:
        print(f"- {trend.metric_name}: {trend.trend_direction} (сила: {trend.trend_strength:.2f})")
    
    # Генерация инсайтов
    insights = analytics.generate_learning_insights()
    print(f"\nСгенерировано инсайтов: {len(insights)}")
    for insight in insights:
        print(f"- {insight.title} (воздействие: {insight.impact_score:.2f})")
    
    # Дашборд
    dashboard = analytics.get_learning_dashboard_data()
    print(f"\nИндекс здоровья системы: {dashboard['overall_health_score']:.2f}")