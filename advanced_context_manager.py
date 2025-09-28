"""
Продвинутая система управления контекстом для максимальной точности бота
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import hashlib
import logging

logger = logging.getLogger(__name__)

@dataclass
class ContextEntry:
    """Запись контекста диалога"""
    timestamp: datetime
    message_type: str  # 'user', 'bot', 'analysis'
    content: str
    metadata: Dict[str, Any]
    importance_score: float  # 0.0-1.0
    topic: Optional[str] = None
    sentiment: Optional[str] = None

@dataclass
class UserProfile:
    """Профиль пользователя"""
    user_id: int
    name: str
    personality_traits: Dict[str, float]
    communication_style: Dict[str, Any]
    preferences: Dict[str, Any]
    last_updated: datetime
    total_interactions: int

class AdvancedContextManager:
    """Продвинутый менеджер контекста для обеспечения точности и последовательности"""
    
    def __init__(self, db_path: str = 'context.db'):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Инициализация базы данных для контекста"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица контекста диалогов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                importance_score REAL NOT NULL,
                topic TEXT,
                sentiment TEXT,
                session_id TEXT,
                context_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица профилей пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                personality_traits TEXT NOT NULL,
                communication_style TEXT NOT NULL,
                preferences TEXT NOT NULL,
                last_updated TIMESTAMP NOT NULL,
                total_interactions INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица сессий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                context_summary TEXT,
                analysis_type TEXT,
                quality_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_timestamp ON context_entries(user_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance ON context_entries(importance_score DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_topic ON context_entries(topic)')
        
        conn.commit()
        conn.close()
    
    def _calculate_importance_score(self, content: str, message_type: str, metadata: Dict) -> float:
        """Вычисляет важность сообщения для контекста"""
        score = 0.5  # Базовая важность
        
        # Повышаем важность для определенных типов сообщений
        if message_type == 'analysis':
            score += 0.3
        elif 'question' in content.lower() or '?' in content:
            score += 0.2
        elif len(content) > 100:  # Длинные сообщения обычно важнее
            score += 0.1
        
        # Ключевые слова повышают важность
        important_keywords = [
            'проблема', 'сложно', 'трудно', 'страшно', 'грустно',
            'работа', 'карьера', 'цели', 'мечты', 'планы',
            'отношения', 'семья', 'друзья', 'любовь'
        ]
        
        content_lower = content.lower()
        for keyword in important_keywords:
            if keyword in content_lower:
                score += 0.05
        
        # Ограничиваем в диапазоне 0.0-1.0
        return min(1.0, max(0.0, score))
    
    def add_context_entry(self, user_id: int, message_type: str, content: str, 
                         metadata: Dict = None, session_id: str = None) -> str:
        """Добавляет запись в контекст"""
        if metadata is None:
            metadata = {}
        
        importance_score = self._calculate_importance_score(content, message_type, metadata)
        
        # Создаем хэш для уникальности контекста
        context_hash = hashlib.md5(f"{user_id}_{content}_{datetime.now()}".encode()).hexdigest()[:12]
        
        entry = ContextEntry(
            timestamp=datetime.now(),
            message_type=message_type,
            content=content,
            metadata=metadata,
            importance_score=importance_score,
            topic=metadata.get('topic'),
            sentiment=metadata.get('sentiment')
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO context_entries 
            (user_id, timestamp, message_type, content, metadata, importance_score, 
             topic, sentiment, session_id, context_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, entry.timestamp, entry.message_type, entry.content,
            json.dumps(entry.metadata), entry.importance_score,
            entry.topic, entry.sentiment, session_id, context_hash
        ))
        
        conn.commit()
        conn.close()
        
        return context_hash
    
    def get_relevant_context(self, user_id: int, max_entries: int = 15, 
                           min_importance: float = 0.3) -> List[ContextEntry]:
        """Получает релевантный контекст для пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, message_type, content, metadata, importance_score, topic, sentiment
            FROM context_entries 
            WHERE user_id = ? AND importance_score >= ?
            ORDER BY importance_score DESC, timestamp DESC
            LIMIT ?
        ''', (user_id, min_importance, max_entries))
        
        entries = []
        for row in cursor.fetchall():
            entry = ContextEntry(
                timestamp=datetime.fromisoformat(row[0]),
                message_type=row[1],
                content=row[2],
                metadata=json.loads(row[3]),
                importance_score=row[4],
                topic=row[5],
                sentiment=row[6]
            )
            entries.append(entry)
        
        conn.close()
        return entries
    
    def update_user_profile(self, user_id: int, name: str, 
                          personality_traits: Dict[str, float],
                          communication_style: Dict[str, Any],
                          preferences: Dict[str, Any]):
        """Обновляет профиль пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Увеличиваем счетчик взаимодействий
        cursor.execute('SELECT total_interactions FROM user_profiles WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        total_interactions = (result[0] if result else 0) + 1
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles 
            (user_id, name, personality_traits, communication_style, preferences, 
             last_updated, total_interactions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, name, json.dumps(personality_traits),
            json.dumps(communication_style), json.dumps(preferences),
            datetime.now(), total_interactions
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Получает профиль пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, personality_traits, communication_style, preferences, 
                   last_updated, total_interactions
            FROM user_profiles WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return UserProfile(
            user_id=user_id,
            name=result[0],
            personality_traits=json.loads(result[1]),
            communication_style=json.loads(result[2]),
            preferences=json.loads(result[3]),
            last_updated=datetime.fromisoformat(result[4]),
            total_interactions=result[5]
        )
    
    def create_session(self, user_id: int) -> str:
        """Создает новую сессию"""
        session_id = hashlib.md5(f"{user_id}_{datetime.now()}".encode()).hexdigest()[:16]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions (session_id, user_id, start_time)
            VALUES (?, ?, ?)
        ''', (session_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def end_session(self, session_id: str, context_summary: str = None, 
                   analysis_type: str = None, quality_score: float = None):
        """Завершает сессию"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sessions 
            SET end_time = ?, context_summary = ?, analysis_type = ?, quality_score = ?
            WHERE session_id = ?
        ''', (datetime.now(), context_summary, analysis_type, quality_score, session_id))
        
        conn.commit()
        conn.close()
    
    def get_session_context(self, session_id: str) -> List[ContextEntry]:
        """Получает контекст конкретной сессии"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, message_type, content, metadata, importance_score, topic, sentiment
            FROM context_entries 
            WHERE session_id = ?
            ORDER BY timestamp ASC
        ''', (session_id,))
        
        entries = []
        for row in cursor.fetchall():
            entry = ContextEntry(
                timestamp=datetime.fromisoformat(row[0]),
                message_type=row[1],
                content=row[2],
                metadata=json.loads(row[3]),
                importance_score=row[4],
                topic=row[5],
                sentiment=row[6]
            )
            entries.append(entry)
        
        conn.close()
        return entries
    
    def cleanup_old_context(self, days_old: int = 30):
        """Очищает старый контекст для экономии места"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM context_entries WHERE timestamp < ?', (cutoff_date,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Очищено {deleted_count} старых записей контекста")
        return deleted_count
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """Получает статистику контекста"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM context_entries')
        total_entries = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM user_profiles')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM sessions')
        total_sessions = cursor.fetchone()[0]
        
        # Статистика по важности
        cursor.execute('SELECT AVG(importance_score) FROM context_entries')
        avg_importance = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_entries': total_entries,
            'total_users': total_users,
            'total_sessions': total_sessions,
            'average_importance': avg_importance
        }

# Глобальный экземпляр менеджера контекста
context_manager = AdvancedContextManager()