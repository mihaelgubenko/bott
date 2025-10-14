"""
Менеджер базы данных с улучшенной архитектурой
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AnalysisRecord:
    """Запись анализа"""
    id: int
    telegram_id: int
    name: str
    analysis_type: str
    analysis_data: Dict[str, Any]
    payment_status: str
    created_at: datetime

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = config.DATABASE_PATH
    
    async def init_database(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица клиентов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    name TEXT,
                    analysis_type TEXT,
                    analysis_data TEXT,
                    payment_status TEXT DEFAULT 'free',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для A/B тестирования промптов
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
            
            # Таблица результатов A/B тестов
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
            
            logger.info("База данных инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    async def save_analysis(
        self, 
        telegram_id: int, 
        name: str, 
        analysis_type: str, 
        analysis_data: Dict[str, Any], 
        payment_status: str = 'free'
    ) -> int:
        """Сохранение анализа"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO clients 
                (telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                telegram_id, 
                name, 
                analysis_type, 
                json.dumps(analysis_data), 
                payment_status, 
                datetime.now()
            ))
            
            analysis_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Анализ сохранен: ID {analysis_id}, пользователь {telegram_id}")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Ошибка сохранения анализа: {e}")
            raise
    
    async def get_user_analyses(self, telegram_id: int) -> List[AnalysisRecord]:
        """Получение анализов пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT * FROM clients WHERE telegram_id = ? ORDER BY created_at DESC', 
                (telegram_id,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            analyses = []
            for row in rows:
                analyses.append(AnalysisRecord(
                    id=row[0],
                    telegram_id=row[1],
                    name=row[2],
                    analysis_type=row[3],
                    analysis_data=json.loads(row[4]) if row[4] else {},
                    payment_status=row[5],
                    created_at=datetime.fromisoformat(row[6])
                ))
            
            return analyses
            
        except Exception as e:
            logger.error(f"Ошибка получения анализов: {e}")
            return []
    
    async def clear_user_data(self, telegram_id: int):
        """Очистка данных пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM clients WHERE telegram_id = ?', (telegram_id,))
            cursor.execute('DELETE FROM ab_test_results WHERE user_id = ?', (telegram_id,))
            cursor.execute('DELETE FROM user_variant_assignments WHERE user_id = ?', (telegram_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Данные пользователя {telegram_id} очищены")
            
        except Exception as e:
            logger.error(f"Ошибка очистки данных пользователя: {e}")
    
    async def clear_all_data(self):
        """Очистка всех данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM clients')
            cursor.execute('DELETE FROM ab_test_results')
            cursor.execute('DELETE FROM user_variant_assignments')
            
            conn.commit()
            conn.close()
            
            logger.info("Все данные очищены")
            
        except Exception as e:
            logger.error(f"Ошибка очистки всех данных: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Получение статуса здоровья базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Подсчет записей
            cursor.execute('SELECT COUNT(*) FROM clients')
            total_clients = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM ab_test_results')
            total_tests = cursor.fetchone()[0]
            
            # Проверка целостности
            cursor.execute('PRAGMA integrity_check')
            integrity_check = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'status': 'healthy' if integrity_check == 'ok' else 'unhealthy',
                'total_clients': total_clients,
                'total_tests': total_tests,
                'integrity_check': integrity_check
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья БД: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }