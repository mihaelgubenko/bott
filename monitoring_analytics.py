"""
Система мониторинга и аналитики для отслеживания точности и производительности бота
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import time
import asyncio

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Типы метрик для мониторинга"""
    RESPONSE_TIME = "response_time"
    QUALITY_SCORE = "quality_score"
    USER_SATISFACTION = "user_satisfaction"
    ERROR_RATE = "error_rate"
    CONVERSION_RATE = "conversion_rate"
    ENGAGEMENT = "engagement"

class AlertLevel(Enum):
    """Уровни алертов"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class MetricData:
    """Данные метрики"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    user_id: Optional[int] = None
    context: Dict[str, Any] = None

@dataclass
class Alert:
    """Алерт системы"""
    level: AlertLevel
    message: str
    metric_type: MetricType
    current_value: float
    threshold_value: float
    timestamp: datetime
    resolved: bool = False

@dataclass
class PerformanceReport:
    """Отчет о производительности"""
    period_start: datetime
    period_end: datetime
    metrics_summary: Dict[str, Any]
    trends: Dict[str, float]
    alerts: List[Alert]
    recommendations: List[str]

class MonitoringAnalytics:
    """Система мониторинга и аналитики"""
    
    def __init__(self, db_path: str = 'monitoring.db'):
        self.db_path = db_path
        self.init_database()
        self._load_thresholds()
        self._setup_metrics_collectors()
    
    def init_database(self):
        """Инициализация базы данных для мониторинга"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица метрик
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                user_id INTEGER,
                context TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица алертов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                current_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP
            )
        ''')
        
        # Таблица сессий пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                analysis_type TEXT,
                satisfaction_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metric_timestamp ON metrics(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metric_type ON metrics(metric_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_timestamp ON alerts(timestamp)')
        
        conn.commit()
        conn.close()
    
    def _load_thresholds(self):
        """Загружает пороговые значения для алертов"""
        self.thresholds = {
            MetricType.RESPONSE_TIME: {
                'warning': 10.0,  # секунды
                'critical': 30.0
            },
            MetricType.QUALITY_SCORE: {
                'warning': 0.6,
                'critical': 0.4
            },
            MetricType.USER_SATISFACTION: {
                'warning': 0.7,
                'critical': 0.5
            },
            MetricType.ERROR_RATE: {
                'warning': 0.05,  # 5%
                'critical': 0.1   # 10%
            },
            MetricType.CONVERSION_RATE: {
                'warning': 0.1,   # 10%
                'critical': 0.05  # 5%
            },
            MetricType.ENGAGEMENT: {
                'warning': 0.5,
                'critical': 0.3
            }
        }
    
    def _setup_metrics_collectors(self):
        """Настраивает сборщики метрик"""
        self.metrics_collectors = {
            MetricType.RESPONSE_TIME: self._collect_response_time_metrics,
            MetricType.QUALITY_SCORE: self._collect_quality_metrics,
            MetricType.USER_SATISFACTION: self._collect_satisfaction_metrics,
            MetricType.ERROR_RATE: self._collect_error_metrics,
            MetricType.CONVERSION_RATE: self._collect_conversion_metrics,
            MetricType.ENGAGEMENT: self._collect_engagement_metrics
        }
    
    def record_metric(self, metric_type: MetricType, value: float, 
                     user_id: int = None, context: Dict[str, Any] = None):
        """Записывает метрику"""
        metric_data = MetricData(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            user_id=user_id,
            context=context or {}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO metrics (metric_type, value, user_id, context, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            metric_data.metric_type.value, metric_data.value,
            metric_data.user_id, json.dumps(metric_data.context),
            metric_data.timestamp
        ))
        
        conn.commit()
        conn.close()
        
        # Проверяем пороговые значения
        self._check_thresholds(metric_data)
    
    def _check_thresholds(self, metric_data: MetricData):
        """Проверяет пороговые значения и создает алерты"""
        thresholds = self.thresholds.get(metric_data.metric_type)
        if not thresholds:
            return
        
        alert_level = None
        threshold_value = None
        
        # Определяем уровень алерта
        if metric_data.value >= thresholds['critical'] or metric_data.value <= thresholds.get('critical_low', float('-inf')):
            alert_level = AlertLevel.CRITICAL
            threshold_value = thresholds['critical']
        elif metric_data.value >= thresholds['warning'] or metric_data.value <= thresholds.get('warning_low', float('-inf')):
            alert_level = AlertLevel.WARNING
            threshold_value = thresholds['warning']
        
        if alert_level:
            alert = Alert(
                level=alert_level,
                message=f"{metric_data.metric_type.value} превысил пороговое значение: {metric_data.value}",
                metric_type=metric_data.metric_type,
                current_value=metric_data.value,
                threshold_value=threshold_value,
                timestamp=datetime.now()
            )
            self._save_alert(alert)
    
    def _save_alert(self, alert: Alert):
        """Сохраняет алерт"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts 
            (level, message, metric_type, current_value, threshold_value, timestamp, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.level.value, alert.message, alert.metric_type.value,
            alert.current_value, alert.threshold_value, alert.timestamp, alert.resolved
        ))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"ALERT [{alert.level.value}]: {alert.message}")
    
    def start_session_monitoring(self, session_id: str, user_id: int) -> str:
        """Начинает мониторинг сессии"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_sessions 
            (session_id, user_id, start_time, message_count)
            VALUES (?, ?, ?, 0)
        ''', (session_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def update_session(self, session_id: str, message_count: int = None, 
                      analysis_type: str = None, satisfaction_score: float = None):
        """Обновляет данные сессии"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if message_count is not None:
            updates.append('message_count = ?')
            values.append(message_count)
        
        if analysis_type is not None:
            updates.append('analysis_type = ?')
            values.append(analysis_type)
        
        if satisfaction_score is not None:
            updates.append('satisfaction_score = ?')
            values.append(satisfaction_score)
        
        if updates:
            values.append(session_id)
            cursor.execute(f'''
                UPDATE user_sessions 
                SET {', '.join(updates)}
                WHERE session_id = ?
            ''', values)
        
        conn.commit()
        conn.close()
    
    def end_session(self, session_id: str, satisfaction_score: float = None):
        """Завершает сессию"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = ['end_time = ?']
        values = [datetime.now()]
        
        if satisfaction_score is not None:
            updates.append('satisfaction_score = ?')
            values.append(satisfaction_score)
        
        values.append(session_id)
        
        cursor.execute(f'''
            UPDATE user_sessions 
            SET {', '.join(updates)}
            WHERE session_id = ?
        ''', values)
        
        conn.commit()
        conn.close()
    
    def _collect_response_time_metrics(self, hours: int = 24) -> List[MetricData]:
        """Собирает метрики времени ответа"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT value, timestamp, user_id, context
            FROM metrics 
            WHERE metric_type = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (MetricType.RESPONSE_TIME.value, cutoff_time))
        
        metrics = []
        for row in cursor.fetchall():
            metric = MetricData(
                metric_type=MetricType.RESPONSE_TIME,
                value=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                user_id=row[2],
                context=json.loads(row[3]) if row[3] else {}
            )
            metrics.append(metric)
        
        conn.close()
        return metrics
    
    def _collect_quality_metrics(self, hours: int = 24) -> List[MetricData]:
        """Собирает метрики качества"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT value, timestamp, user_id, context
            FROM metrics 
            WHERE metric_type = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (MetricType.QUALITY_SCORE.value, cutoff_time))
        
        metrics = []
        for row in cursor.fetchall():
            metric = MetricData(
                metric_type=MetricType.QUALITY_SCORE,
                value=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                user_id=row[2],
                context=json.loads(row[3]) if row[3] else {}
            )
            metrics.append(metric)
        
        conn.close()
        return metrics
    
    def _collect_satisfaction_metrics(self, hours: int = 24) -> List[MetricData]:
        """Собирает метрики удовлетворенности"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT AVG(satisfaction_score) as avg_satisfaction, 
                   COUNT(*) as session_count,
                   MAX(timestamp) as last_session
            FROM user_sessions 
            WHERE end_time >= ? AND satisfaction_score IS NOT NULL
        ''', (cutoff_time,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] is not None:
            metric = MetricData(
                metric_type=MetricType.USER_SATISFACTION,
                value=result[0],
                timestamp=datetime.now(),
                context={'session_count': result[1], 'last_session': result[2]}
            )
            return [metric]
        
        return []
    
    def _collect_error_metrics(self, hours: int = 24) -> List[MetricData]:
        """Собирает метрики ошибок"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total_requests
            FROM metrics 
            WHERE timestamp >= ?
        ''', (cutoff_time,))
        
        total_requests = cursor.fetchone()[0] or 1
        
        cursor.execute('''
            SELECT COUNT(*) as error_count
            FROM metrics 
            WHERE metric_type = 'error_rate' AND timestamp >= ?
        ''', (cutoff_time,))
        
        error_count = cursor.fetchone()[0] or 0
        
        error_rate = error_count / total_requests
        
        metric = MetricData(
            metric_type=MetricType.ERROR_RATE,
            value=error_rate,
            timestamp=datetime.now(),
            context={'total_requests': total_requests, 'error_count': error_count}
        )
        
        conn.close()
        return [metric]
    
    def _collect_conversion_metrics(self, hours: int = 24) -> List[MetricData]:
        """Собирает метрики конверсии"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total_sessions
            FROM user_sessions 
            WHERE start_time >= ?
        ''', (cutoff_time,))
        
        total_sessions = cursor.fetchone()[0] or 1
        
        cursor.execute('''
            SELECT COUNT(*) as paid_sessions
            FROM user_sessions 
            WHERE start_time >= ? AND analysis_type = 'full'
        ''', (cutoff_time,))
        
        paid_sessions = cursor.fetchone()[0] or 0
        
        conversion_rate = paid_sessions / total_sessions
        
        metric = MetricData(
            metric_type=MetricType.CONVERSION_RATE,
            value=conversion_rate,
            timestamp=datetime.now(),
            context={'total_sessions': total_sessions, 'paid_sessions': paid_sessions}
        )
        
        conn.close()
        return [metric]
    
    def _collect_engagement_metrics(self, hours: int = 24) -> List[MetricData]:
        """Собирает метрики вовлеченности"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT AVG(message_count) as avg_messages,
                   AVG((julianday(end_time) - julianday(start_time)) * 24 * 60) as avg_duration_minutes
            FROM user_sessions 
            WHERE start_time >= ? AND end_time IS NOT NULL
        ''', (cutoff_time,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] is not None:
            # Нормализуем к 0-1 (средняя вовлеченность)
            avg_messages = result[0] or 0
            avg_duration = result[1] or 0
            
            # Простая нормализация
            message_score = min(1.0, avg_messages / 20.0)  # 20 сообщений = 1.0
            duration_score = min(1.0, avg_duration / 60.0)  # 60 минут = 1.0
            
            engagement_score = (message_score + duration_score) / 2
            
            metric = MetricData(
                metric_type=MetricType.ENGAGEMENT,
                value=engagement_score,
                timestamp=datetime.now(),
                context={'avg_messages': avg_messages, 'avg_duration': avg_duration}
            )
            return [metric]
        
        return []
    
    def generate_performance_report(self, hours: int = 24) -> PerformanceReport:
        """Генерирует отчет о производительности"""
        period_end = datetime.now()
        period_start = period_end - timedelta(hours=hours)
        
        # Собираем все метрики
        all_metrics = {}
        for metric_type, collector in self.metrics_collectors.items():
            metrics = collector(hours)
            all_metrics[metric_type.value] = metrics
        
        # Вычисляем тренды
        trends = self._calculate_trends(all_metrics)
        
        # Получаем активные алерты
        active_alerts = self._get_active_alerts()
        
        # Генерируем рекомендации
        recommendations = self._generate_recommendations(all_metrics, trends, active_alerts)
        
        # Создаем сводку метрик
        metrics_summary = {}
        for metric_type, metrics in all_metrics.items():
            if metrics:
                values = [m.value for m in metrics]
                metrics_summary[metric_type] = {
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values),
                    'latest': values[0] if values else 0
                }
            else:
                metrics_summary[metric_type] = {
                    'average': 0,
                    'min': 0,
                    'max': 0,
                    'count': 0,
                    'latest': 0
                }
        
        return PerformanceReport(
            period_start=period_start,
            period_end=period_end,
            metrics_summary=metrics_summary,
            trends=trends,
            alerts=active_alerts,
            recommendations=recommendations
        )
    
    def _calculate_trends(self, all_metrics: Dict[str, List[MetricData]]) -> Dict[str, float]:
        """Вычисляет тренды метрик"""
        trends = {}
        
        for metric_type, metrics in all_metrics.items():
            if len(metrics) < 2:
                trends[metric_type] = 0.0
                continue
            
            # Простой тренд: сравнение первой и последней половины
            mid_point = len(metrics) // 2
            first_half = [m.value for m in metrics[mid_point:]]
            second_half = [m.value for m in metrics[:mid_point]]
            
            if first_half and second_half:
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)
                trend = (second_avg - first_avg) / first_avg if first_avg != 0 else 0
                trends[metric_type] = trend
            else:
                trends[metric_type] = 0.0
        
        return trends
    
    def _get_active_alerts(self) -> List[Alert]:
        """Получает активные алерты"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT level, message, metric_type, current_value, threshold_value, timestamp
            FROM alerts 
            WHERE resolved = FALSE
            ORDER BY timestamp DESC
        ''', ())
        
        alerts = []
        for row in cursor.fetchall():
            alert = Alert(
                level=AlertLevel(row[0]),
                message=row[1],
                metric_type=MetricType(row[2]),
                current_value=row[3],
                threshold_value=row[4],
                timestamp=datetime.fromisoformat(row[5])
            )
            alerts.append(alert)
        
        conn.close()
        return alerts
    
    def _generate_recommendations(self, metrics: Dict, trends: Dict, alerts: List[Alert]) -> List[str]:
        """Генерирует рекомендации на основе анализа"""
        recommendations = []
        
        # Рекомендации на основе алертов
        for alert in alerts:
            if alert.metric_type == MetricType.RESPONSE_TIME:
                recommendations.append("Оптимизировать время ответа: проверить производительность API")
            elif alert.metric_type == MetricType.QUALITY_SCORE:
                recommendations.append("Улучшить качество ответов: пересмотреть промпты")
            elif alert.metric_type == MetricType.USER_SATISFACTION:
                recommendations.append("Повысить удовлетворенность пользователей: добавить персонализацию")
        
        # Рекомендации на основе трендов
        for metric_type, trend in trends.items():
            if trend < -0.1:  # Падающий тренд
                if metric_type == 'quality_score':
                    recommendations.append("Качество ответов снижается - требуется анализ промптов")
                elif metric_type == 'engagement':
                    recommendations.append("Вовлеченность падает - улучшить интерактивность")
        
        # Общие рекомендации
        if not recommendations:
            recommendations.append("Система работает стабильно - продолжить мониторинг")
        
        return recommendations
    
    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """Получает данные для дашборда в реальном времени"""
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'alerts': {},
            'status': 'healthy'
        }
        
        # Получаем последние значения метрик
        for metric_type in MetricType:
            metrics = self.metrics_collectors[metric_type](1)  # Последний час
            if metrics:
                latest_metric = metrics[0]
                dashboard_data['metrics'][metric_type.value] = {
                    'value': latest_metric.value,
                    'timestamp': latest_metric.timestamp.isoformat()
                }
        
        # Получаем активные алерты
        active_alerts = self._get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL]
        warning_alerts = [a for a in active_alerts if a.level == AlertLevel.WARNING]
        
        dashboard_data['alerts'] = {
            'critical_count': len(critical_alerts),
            'warning_count': len(warning_alerts),
            'total_count': len(active_alerts)
        }
        
        # Определяем общий статус
        if critical_alerts:
            dashboard_data['status'] = 'critical'
        elif warning_alerts:
            dashboard_data['status'] = 'warning'
        
        return dashboard_data

# Глобальный экземпляр системы мониторинга
monitoring_system = MonitoringAnalytics()