"""
Модуль для синхронизации данных чатов между разными средами
Поддерживает экспорт/импорт в JSON, CSV и облачные хранилища
"""

import json
import csv
import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ChatData:
    """Структура данных чата для синхронизации"""
    telegram_id: int
    name: str
    analysis_type: str  # 'express' or 'full'
    analysis_data: Dict[str, Any]
    payment_status: str
    created_at: str
    conversation_history: List[str] = None
    ab_test_results: List[Dict] = None

class DataSyncManager:
    """Менеджер синхронизации данных чатов"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.export_dir = Path('exports')
        self.export_dir.mkdir(exist_ok=True)
    
    def export_all_data(self, format_type: str = 'json') -> str:
        """Экспорт всех данных в файл"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'json':
            return self._export_to_json(timestamp)
        elif format_type == 'csv':
            return self._export_to_csv(timestamp)
        else:
            raise ValueError(f"Неподдерживаемый формат: {format_type}")
    
    def _export_to_json(self, timestamp: str) -> str:
        """Экспорт в JSON формат"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем все анализы
        cursor.execute('SELECT * FROM clients ORDER BY created_at DESC')
        analyses = cursor.fetchall()
        
        # Получаем результаты A/B тестов
        cursor.execute('SELECT * FROM ab_test_results ORDER BY timestamp DESC')
        ab_results = cursor.fetchall()
        
        # Получаем назначения вариантов
        cursor.execute('SELECT * FROM user_variant_assignments')
        variant_assignments = cursor.fetchall()
        
        conn.close()
        
        # Формируем структуру данных
        export_data = {
            'export_info': {
                'timestamp': timestamp,
                'exported_at': datetime.now().isoformat(),
                'total_analyses': len(analyses),
                'total_ab_results': len(ab_results),
                'version': '2.1'
            },
            'analyses': [],
            'ab_test_results': [],
            'variant_assignments': []
        }
        
        # Обрабатываем анализы
        for analysis in analyses:
            analysis_data = {
                'id': analysis[0],
                'telegram_id': analysis[1],
                'name': analysis[2],
                'analysis_type': analysis[3],
                'analysis_data': json.loads(analysis[4]) if analysis[4] else {},
                'payment_status': analysis[5],
                'created_at': analysis[6]
            }
            export_data['analyses'].append(analysis_data)
        
        # Обрабатываем результаты A/B тестов
        for result in ab_results:
            ab_data = {
                'id': result[0],
                'user_id': result[1],
                'prompt_variant_id': result[2],
                'prompt_type': result[3],
                'user_feedback': result[4],
                'response_quality': result[5],
                'user_engagement': result[6],
                'conversion': bool(result[7]),
                'timestamp': result[8]
            }
            export_data['ab_test_results'].append(ab_data)
        
        # Обрабатываем назначения вариантов
        for assignment in variant_assignments:
            assignment_data = {
                'user_id': assignment[0],
                'prompt_type': assignment[1],
                'variant_id': assignment[2],
                'assigned_at': assignment[3]
            }
            export_data['variant_assignments'].append(assignment_data)
        
        # Сохраняем в файл
        filename = f"psychoanalyst_export_{timestamp}.json"
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Данные экспортированы в {filepath}")
        return str(filepath)
    
    def _export_to_csv(self, timestamp: str) -> str:
        """Экспорт в CSV формат"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Экспортируем анализы
        cursor.execute('SELECT * FROM clients ORDER BY created_at DESC')
        analyses = cursor.fetchall()
        
        filename = f"psychoanalyst_analyses_{timestamp}.csv"
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Telegram ID', 'Name', 'Analysis Type', 'Analysis Data', 'Payment Status', 'Created At'])
            
            for analysis in analyses:
                writer.writerow(analysis)
        
        # Экспортируем результаты A/B тестов
        cursor.execute('SELECT * FROM ab_test_results ORDER BY timestamp DESC')
        ab_results = cursor.fetchall()
        
        ab_filename = f"psychoanalyst_ab_results_{timestamp}.csv"
        ab_filepath = self.export_dir / ab_filename
        
        with open(ab_filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'User ID', 'Prompt Variant ID', 'Prompt Type', 'User Feedback', 'Response Quality', 'User Engagement', 'Conversion', 'Timestamp'])
            
            for result in ab_results:
                writer.writerow(result)
        
        conn.close()
        
        logger.info(f"Данные экспортированы в {filepath} и {ab_filepath}")
        return str(filepath)
    
    def import_data(self, filepath: str, merge_mode: bool = True) -> Dict[str, int]:
        """Импорт данных из файла"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл не найден: {filepath}")
        
        if filepath.endswith('.json'):
            return self._import_from_json(filepath, merge_mode)
        elif filepath.endswith('.csv'):
            return self._import_from_csv(filepath, merge_mode)
        else:
            raise ValueError("Поддерживаются только JSON и CSV файлы")
    
    def _import_from_json(self, filepath: str, merge_mode: bool) -> Dict[str, int]:
        """Импорт из JSON файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        imported_counts = {
            'analyses': 0,
            'ab_results': 0,
            'assignments': 0
        }
        
        try:
            # Импортируем анализы
            for analysis in data.get('analyses', []):
                if merge_mode:
                    cursor.execute('''
                        INSERT OR REPLACE INTO clients 
                        (id, telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        analysis['id'],
                        analysis['telegram_id'],
                        analysis['name'],
                        analysis['analysis_type'],
                        json.dumps(analysis['analysis_data']),
                        analysis['payment_status'],
                        analysis['created_at']
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO clients 
                        (telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        analysis['telegram_id'],
                        analysis['name'],
                        analysis['analysis_type'],
                        json.dumps(analysis['analysis_data']),
                        analysis['payment_status'],
                        analysis['created_at']
                    ))
                imported_counts['analyses'] += 1
            
            # Импортируем результаты A/B тестов
            for result in data.get('ab_test_results', []):
                if merge_mode:
                    cursor.execute('''
                        INSERT OR REPLACE INTO ab_test_results 
                        (id, user_id, prompt_variant_id, prompt_type, user_feedback, response_quality, user_engagement, conversion, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result['id'],
                        result['user_id'],
                        result['prompt_variant_id'],
                        result['prompt_type'],
                        result['user_feedback'],
                        result['response_quality'],
                        result['user_engagement'],
                        result['conversion'],
                        result['timestamp']
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO ab_test_results 
                        (user_id, prompt_variant_id, prompt_type, user_feedback, response_quality, user_engagement, conversion, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result['user_id'],
                        result['prompt_variant_id'],
                        result['prompt_type'],
                        result['user_feedback'],
                        result['response_quality'],
                        result['user_engagement'],
                        result['conversion'],
                        result['timestamp']
                    ))
                imported_counts['ab_results'] += 1
            
            # Импортируем назначения вариантов
            for assignment in data.get('variant_assignments', []):
                if merge_mode:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_variant_assignments 
                        (user_id, prompt_type, variant_id, assigned_at)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        assignment['user_id'],
                        assignment['prompt_type'],
                        assignment['variant_id'],
                        assignment['assigned_at']
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO user_variant_assignments 
                        (user_id, prompt_type, variant_id, assigned_at)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        assignment['user_id'],
                        assignment['prompt_type'],
                        assignment['variant_id'],
                        assignment['assigned_at']
                    ))
                imported_counts['assignments'] += 1
            
            conn.commit()
            logger.info(f"Импортировано: {imported_counts}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при импорте: {e}")
            raise
        finally:
            conn.close()
        
        return imported_counts
    
    def _import_from_csv(self, filepath: str, merge_mode: bool) -> Dict[str, int]:
        """Импорт из CSV файла"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        imported_count = 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  # Пропускаем заголовок
                
                for row in reader:
                    if len(row) >= 7:  # Минимальное количество полей для анализа
                        if merge_mode:
                            cursor.execute('''
                                INSERT OR REPLACE INTO clients 
                                (id, telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', row)
                        else:
                            cursor.execute('''
                                INSERT INTO clients 
                                (telegram_id, name, analysis_type, analysis_data, payment_status, created_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', row[1:])  # Пропускаем ID
                        imported_count += 1
            
            conn.commit()
            logger.info(f"Импортировано {imported_count} записей из CSV")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при импорте CSV: {e}")
            raise
        finally:
            conn.close()
        
        return {'analyses': imported_count, 'ab_results': 0, 'assignments': 0}
    
    def get_export_info(self) -> Dict[str, Any]:
        """Получить информацию о доступных экспортах"""
        exports = []
        
        for file in self.export_dir.glob('psychoanalyst_export_*.json'):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    exports.append({
                        'filename': file.name,
                        'filepath': str(file),
                        'exported_at': data.get('export_info', {}).get('exported_at'),
                        'total_analyses': data.get('export_info', {}).get('total_analyses', 0),
                        'file_size': file.stat().st_size
                    })
            except Exception as e:
                logger.error(f"Ошибка при чтении файла {file}: {e}")
        
        return {
            'export_dir': str(self.export_dir),
            'available_exports': exports,
            'total_exports': len(exports)
        }
    
    def upload_to_cloud(self, filepath: str, cloud_service: str = 'gdrive') -> str:
        """Загрузка файла в облачное хранилище"""
        if cloud_service == 'gdrive':
            return self._upload_to_gdrive(filepath)
        elif cloud_service == 'dropbox':
            return self._upload_to_dropbox(filepath)
        else:
            raise ValueError(f"Неподдерживаемый облачный сервис: {cloud_service}")
    
    def _upload_to_gdrive(self, filepath: str) -> str:
        """Загрузка в Google Drive (требует настройки API)"""
        # Здесь нужно будет добавить интеграцию с Google Drive API
        # Пока возвращаем заглушку
        logger.info(f"Загрузка в Google Drive: {filepath}")
        return f"gdrive://{os.path.basename(filepath)}"
    
    def _upload_to_dropbox(self, filepath: str) -> str:
        """Загрузка в Dropbox (требует настройки API)"""
        # Здесь нужно будет добавить интеграцию с Dropbox API
        # Пока возвращаем заглушку
        logger.info(f"Загрузка в Dropbox: {filepath}")
        return f"dropbox://{os.path.basename(filepath)}"

def get_sync_manager(db_path: str = 'psychoanalyst.db') -> DataSyncManager:
    """Фабричная функция для получения менеджера синхронизации"""
    return DataSyncManager(db_path)

# Пример использования
if __name__ == "__main__":
    sync_manager = get_sync_manager()
    
    # Экспорт данных
    print("Экспорт данных...")
    json_file = sync_manager.export_all_data('json')
    print(f"Экспорт завершен: {json_file}")
    
    # Информация об экспортах
    info = sync_manager.get_export_info()
    print(f"\nДоступно экспортов: {info['total_exports']}")
    for export in info['available_exports']:
        print(f"- {export['filename']} ({export['total_analyses']} анализов)")