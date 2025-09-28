"""
Система обратной связи для непрерывного улучшения точности бота
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """Типы обратной связи"""
    USER_RATING = "user_rating"
    IMPLICIT_BEHAVIOR = "implicit_behavior"
    CONVERSATION_FLOW = "conversation_flow"
    ERROR_DETECTION = "error_detection"

class FeedbackSource(Enum):
    """Источники обратной связи"""
    EXPLICIT_USER = "explicit_user"
    CONVERSATION_CONTINUATION = "conversation_continuation"
    MESSAGE_LENGTH = "message_length"
    RESPONSE_TIME = "response_time"
    SESSION_DURATION = "session_duration"

@dataclass
class FeedbackEntry:
    """Запись обратной связи"""
    user_id: int
    feedback_type: FeedbackType
    source: FeedbackSource
    value: float  # 0.0-1.0 или -1.0-1.0 для рейтингов
    context: Dict[str, Any]
    timestamp: datetime
    response_id: Optional[str] = None

@dataclass
class ImprovementAction:
    """Действие для улучшения"""
    action_type: str
    description: str
    priority: int  # 1-10
    parameters: Dict[str, Any]
    expected_impact: float

class FeedbackImprovementSystem:
    """Система обратной связи для улучшения бота"""
    
    def __init__(self, db_path: str = 'feedback.db'):
        self.db_path = db_path
        self.init_database()
        self._load_improvement_patterns()
    
    def init_database(self):
        """Инициализация базы данных для обратной связи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                feedback_type TEXT NOT NULL,
                source TEXT NOT NULL,
                value REAL NOT NULL,
                context TEXT NOT NULL,
                response_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS improvement_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                priority INTEGER NOT NULL,
                parameters TEXT NOT NULL,
                expected_impact REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                implemented_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_patterns (
                pattern_name TEXT PRIMARY KEY,
                pattern_data TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_improvement_patterns(self):
        """Загружает паттерны для анализа обратной связи"""
        self.improvement_patterns = {
            'low_engagement': {
                'triggers': ['short_responses', 'quick_exit', 'low_rating'],
                'actions': ['simplify_language', 'add_questions', 'improve_empathy']
            },
            'high_engagement': {
                'triggers': ['long_responses', 'multiple_questions', 'high_rating'],
                'actions': ['provide_deeper_analysis', 'offer_advanced_features']
            },
            'confusion_signals': {
                'triggers': ['clarification_requests', 'topic_changes', 'negative_feedback'],
                'actions': ['improve_clarity', 'better_context_handling']
            },
            'success_signals': {
                'triggers': ['thanks_messages', 'positive_keywords', 'session_continuation'],
                'actions': ['maintain_current_approach', 'optimize_successful_patterns']
            }
        }
    
    def record_feedback(self, user_id: int, feedback_type: FeedbackType, 
                       source: FeedbackSource, value: float, 
                       context: Dict[str, Any], response_id: str = None):
        """Записывает обратную связь"""
        entry = FeedbackEntry(
            user_id=user_id,
            feedback_type=feedback_type,
            source=source,
            value=value,
            context=context,
            timestamp=datetime.now(),
            response_id=response_id
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback_entries 
            (user_id, feedback_type, source, value, context, response_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.user_id, entry.feedback_type.value, entry.source.value,
            entry.value, json.dumps(entry.context), entry.response_id, entry.timestamp
        ))
        
        conn.commit()
        conn.close()
        
        # Анализируем обратную связь для улучшений
        self._analyze_feedback_for_improvements(entry)
    
    def analyze_user_behavior(self, user_id: int, session_data: Dict[str, Any]) -> Dict[str, float]:
        """Анализирует поведение пользователя для неявной обратной связи"""
        feedback_scores = {}
        
        # Анализ длины ответов пользователя
        message_lengths = session_data.get('message_lengths', [])
        if message_lengths:
            avg_length = sum(message_lengths) / len(message_lengths)
            # Длинные сообщения = высокая вовлеченность
            engagement_score = min(1.0, avg_length / 200.0)
            feedback_scores['engagement'] = engagement_score
        
        # Анализ времени ответа
        response_times = session_data.get('response_times', [])
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            # Быстрые ответы = высокая вовлеченность
            response_engagement = max(0.0, 1.0 - (avg_response_time / 300.0))  # 5 минут
            feedback_scores['response_engagement'] = response_engagement
        
        # Анализ продолжительности сессии
        session_duration = session_data.get('session_duration', 0)
        duration_score = min(1.0, session_duration / 1800.0)  # 30 минут
        feedback_scores['session_engagement'] = duration_score
        
        # Анализ количества сообщений
        message_count = session_data.get('message_count', 0)
        message_score = min(1.0, message_count / 20.0)  # 20 сообщений
        feedback_scores['message_engagement'] = message_score
        
        return feedback_scores
    
    def detect_implicit_feedback(self, user_id: int, conversation_history: List[str],
                               current_message: str) -> List[FeedbackEntry]:
        """Обнаруживает неявную обратную связь из сообщений пользователя"""
        feedback_entries = []
        
        # Анализ эмоциональных сигналов
        emotional_signals = self._analyze_emotional_signals(current_message)
        for signal_type, value in emotional_signals.items():
            if value != 0:  # Только значимые сигналы
                entry = FeedbackEntry(
                    user_id=user_id,
                    feedback_type=FeedbackType.IMPLICIT_BEHAVIOR,
                    source=FeedbackSource.CONVERSATION_CONTINUATION,
                    value=value,
                    context={'signal_type': signal_type, 'message': current_message},
                    timestamp=datetime.now()
                )
                feedback_entries.append(entry)
        
        # Анализ запросов на уточнение
        if self._is_clarification_request(current_message):
            entry = FeedbackEntry(
                user_id=user_id,
                feedback_type=FeedbackType.ERROR_DETECTION,
                source=FeedbackSource.CONVERSATION_CONTINUATION,
                value=-0.5,  # Негативная обратная связь
                context={'issue': 'confusion', 'message': current_message},
                timestamp=datetime.now()
            )
            feedback_entries.append(entry)
        
        # Анализ благодарности и положительных сигналов
        if self._is_positive_feedback(current_message):
            entry = FeedbackEntry(
                user_id=user_id,
                feedback_type=FeedbackType.USER_RATING,
                source=FeedbackSource.EXPLICIT_USER,
                value=0.8,  # Положительная обратная связь
                context={'signal': 'positive', 'message': current_message},
                timestamp=datetime.now()
            )
            feedback_entries.append(entry)
        
        return feedback_entries
    
    def _analyze_emotional_signals(self, message: str) -> Dict[str, float]:
        """Анализирует эмоциональные сигналы в сообщении"""
        message_lower = message.lower()
        signals = {}
        
        # Положительные сигналы
        positive_keywords = ['спасибо', 'отлично', 'понятно', 'хорошо', 'да', 'согласен']
        positive_count = sum(1 for keyword in positive_keywords if keyword in message_lower)
        signals['positive'] = min(1.0, positive_count * 0.2)
        
        # Негативные сигналы
        negative_keywords = ['не понял', 'не понимаю', 'неправильно', 'не то', 'нет', 'не']
        negative_count = sum(1 for keyword in negative_keywords if keyword in message_lower)
        signals['negative'] = -min(1.0, negative_count * 0.2)
        
        # Сигналы замешательства
        confusion_keywords = ['что?', 'как?', 'почему?', 'объясни', 'не понял']
        confusion_count = sum(1 for keyword in confusion_keywords if keyword in message_lower)
        signals['confusion'] = -min(1.0, confusion_count * 0.3)
        
        return signals
    
    def _is_clarification_request(self, message: str) -> bool:
        """Определяет, является ли сообщение запросом на уточнение"""
        clarification_patterns = [
            'не понял', 'не понимаю', 'что вы имеете в виду', 'объясните',
            'повторите', 'можете объяснить', 'не совсем понятно'
        ]
        message_lower = message.lower()
        return any(pattern in message_lower for pattern in clarification_patterns)
    
    def _is_positive_feedback(self, message: str) -> bool:
        """Определяет, является ли сообщение положительной обратной связью"""
        positive_patterns = [
            'спасибо', 'отлично', 'понятно', 'хорошо', 'да, точно',
            'именно то что нужно', 'помогло', 'полезно'
        ]
        message_lower = message.lower()
        return any(pattern in message_lower for pattern in positive_patterns)
    
    def _analyze_feedback_for_improvements(self, feedback_entry: FeedbackEntry):
        """Анализирует обратную связь и предлагает улучшения"""
        improvements = []
        
        # Анализ негативной обратной связи
        if feedback_entry.value < -0.3:
            if feedback_entry.context.get('signal_type') == 'confusion':
                improvements.append(ImprovementAction(
                    action_type='improve_clarity',
                    description='Улучшить ясность ответов',
                    priority=8,
                    parameters={'target_metric': 'clarity', 'increase_by': 0.2},
                    expected_impact=0.3
                ))
            elif feedback_entry.value < -0.6:
                improvements.append(ImprovementAction(
                    action_type='improve_relevance',
                    description='Улучшить релевантность ответов',
                    priority=9,
                    parameters={'target_metric': 'relevance', 'increase_by': 0.3},
                    expected_impact=0.4
                ))
        
        # Анализ положительной обратной связи
        elif feedback_entry.value > 0.6:
            improvements.append(ImprovementAction(
                action_type='maintain_success',
                description='Поддерживать успешный подход',
                priority=3,
                parameters={'pattern': 'successful_response'},
                expected_impact=0.1
            ))
        
        # Сохраняем предложения по улучшению
        for improvement in improvements:
            self._save_improvement_action(improvement)
    
    def _save_improvement_action(self, action: ImprovementAction):
        """Сохраняет действие для улучшения"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO improvement_actions 
            (action_type, description, priority, parameters, expected_impact, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            action.action_type, action.description, action.priority,
            json.dumps(action.parameters), action.expected_impact, 'pending'
        ))
        
        conn.commit()
        conn.close()
    
    def get_pending_improvements(self, limit: int = 10) -> List[ImprovementAction]:
        """Получает ожидающие улучшения"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT action_type, description, priority, parameters, expected_impact
            FROM improvement_actions 
            WHERE status = 'pending'
            ORDER BY priority DESC, expected_impact DESC
            LIMIT ?
        ''', (limit,))
        
        improvements = []
        for row in cursor.fetchall():
            action = ImprovementAction(
                action_type=row[0],
                description=row[1],
                priority=row[2],
                parameters=json.loads(row[3]),
                expected_impact=row[4]
            )
            improvements.append(action)
        
        conn.close()
        return improvements
    
    def mark_improvement_implemented(self, action_type: str, impact_achieved: float):
        """Отмечает улучшение как реализованное"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE improvement_actions 
            SET status = 'implemented', implemented_at = ?
            WHERE action_type = ? AND status = 'pending'
        ''', (datetime.now(), action_type))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Improvement {action_type} implemented with impact {impact_achieved}")
    
    def get_feedback_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Получает статистику обратной связи"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('''
            SELECT COUNT(*), AVG(value), MIN(value), MAX(value)
            FROM feedback_entries 
            WHERE timestamp >= ?
        ''', (cutoff_date,))
        
        result = cursor.fetchone()
        overall_stats = {
            'total_feedback': result[0] or 0,
            'average_rating': result[1] or 0.0,
            'min_rating': result[2] or 0.0,
            'max_rating': result[3] or 0.0
        }
        
        # Статистика по типам
        cursor.execute('''
            SELECT feedback_type, COUNT(*), AVG(value)
            FROM feedback_entries 
            WHERE timestamp >= ?
            GROUP BY feedback_type
        ''', (cutoff_date,))
        
        type_stats = {}
        for row in cursor.fetchall():
            type_stats[row[0]] = {
                'count': row[1],
                'average_value': row[2] or 0.0
            }
        
        conn.close()
        
        return {
            'overall': overall_stats,
            'by_type': type_stats,
            'period_days': days
        }
    
    def generate_improvement_report(self) -> Dict[str, Any]:
        """Генерирует отчет по улучшениям"""
        pending_improvements = self.get_pending_improvements()
        feedback_stats = self.get_feedback_statistics()
        
        # Анализируем приоритеты
        high_priority = [imp for imp in pending_improvements if imp.priority >= 8]
        medium_priority = [imp for imp in pending_improvements if 5 <= imp.priority < 8]
        low_priority = [imp for imp in pending_improvements if imp.priority < 5]
        
        report = {
            'summary': {
                'total_pending_improvements': len(pending_improvements),
                'high_priority_count': len(high_priority),
                'medium_priority_count': len(medium_priority),
                'low_priority_count': len(low_priority),
                'average_feedback_rating': feedback_stats['overall']['average_rating']
            },
            'recommendations': {
                'immediate_actions': [imp.description for imp in high_priority[:3]],
                'short_term_actions': [imp.description for imp in medium_priority[:5]],
                'long_term_actions': [imp.description for imp in low_priority[:3]]
            },
            'feedback_insights': feedback_stats
        }
        
        return report

# Глобальный экземпляр системы обратной связи
feedback_system = FeedbackImprovementSystem()