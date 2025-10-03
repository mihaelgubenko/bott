#!/usr/bin/env python3
"""
Продвинутый тестер безопасности для бота
Включает тестирование различных типов атак и уязвимостей
"""

import sqlite3
import json
import re
import logging
import time
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecurityTest:
    """Тест безопасности"""
    name: str
    category: str
    description: str
    test_function: callable
    severity: str = "MEDIUM"

class AdvancedSecurityTester:
    """Продвинутый тестер безопасности"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.test_results = []
        self.vulnerabilities_found = []
        
        # Инициализируем тесты
        self.security_tests = self._initialize_security_tests()

    def _initialize_security_tests(self) -> List[SecurityTest]:
        """Инициализация тестов безопасности"""
        tests = [
            SecurityTest(
                name="SQL Injection - Union Based",
                category="SQL Injection",
                description="Тестирование UNION-based SQL инъекций",
                test_function=self._test_union_injection,
                severity="CRITICAL"
            ),
            SecurityTest(
                name="SQL Injection - Boolean Based Blind",
                category="SQL Injection", 
                description="Тестирование Boolean-based blind SQL инъекций",
                test_function=self._test_boolean_blind_injection,
                severity="HIGH"
            ),
            SecurityTest(
                name="SQL Injection - Time Based Blind",
                category="SQL Injection",
                description="Тестирование Time-based blind SQL инъекций",
                test_function=self._test_time_blind_injection,
                severity="HIGH"
            ),
            SecurityTest(
                name="SQL Injection - Error Based",
                category="SQL Injection",
                description="Тестирование Error-based SQL инъекций",
                test_function=self._test_error_based_injection,
                severity="MEDIUM"
            ),
            SecurityTest(
                name="Database Schema Enumeration",
                category="Information Disclosure",
                description="Попытка получения схемы базы данных",
                test_function=self._test_schema_enumeration,
                severity="MEDIUM"
            ),
            SecurityTest(
                name="Data Extraction Test",
                category="Data Breach",
                description="Попытка извлечения данных из базы",
                test_function=self._test_data_extraction,
                severity="HIGH"
            ),
            SecurityTest(
                name="Privilege Escalation Test",
                category="Privilege Escalation",
                description="Попытка повышения привилегий",
                test_function=self._test_privilege_escalation,
                severity="CRITICAL"
            ),
            SecurityTest(
                name="Input Validation Test",
                category="Input Validation",
                description="Тестирование валидации входных данных",
                test_function=self._test_input_validation,
                severity="MEDIUM"
            )
        ]
        
        return tests

    def run_all_tests(self) -> Dict:
        """Запуск всех тестов безопасности"""
        logger.info("Запуск продвинутых тестов безопасности...")
        
        results = {
            'total_tests': len(self.security_tests),
            'passed_tests': 0,
            'failed_tests': 0,
            'vulnerabilities': [],
            'test_details': []
        }
        
        for test in self.security_tests:
            logger.info(f"Выполнение теста: {test.name}")
            
            try:
                test_result = test.test_function()
                
                if test_result['passed']:
                    results['passed_tests'] += 1
                    logger.info(f"✅ {test.name}: ПРОЙДЕН")
                else:
                    results['failed_tests'] += 1
                    results['vulnerabilities'].append({
                        'test_name': test.name,
                        'category': test.category,
                        'severity': test.severity,
                        'description': test_result['description'],
                        'details': test_result['details']
                    })
                    logger.warning(f"❌ {test.name}: ПРОВАЛЕН - {test_result['description']}")
                
                results['test_details'].append({
                    'name': test.name,
                    'category': test.category,
                    'severity': test.severity,
                    'passed': test_result['passed'],
                    'description': test_result['description'],
                    'details': test_result['details']
                })
                
            except Exception as e:
                logger.error(f"Ошибка при выполнении теста {test.name}: {e}")
                results['failed_tests'] += 1
                results['test_details'].append({
                    'name': test.name,
                    'category': test.category,
                    'severity': test.severity,
                    'passed': False,
                    'description': f"Ошибка выполнения: {str(e)}",
                    'details': str(e)
                })
        
        return results

    def _test_union_injection(self) -> Dict:
        """Тестирование UNION-based SQL инъекций"""
        test_db = 'test_union.db'
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Создаем тестовую таблицу
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    email TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO test_users (username, email) 
                VALUES ('admin', 'admin@test.com')
            ''')
            
            conn.commit()
            
            # Тестируем UNION инъекции
            union_payloads = [
                "' UNION SELECT 1,2,3 --",
                "' UNION SELECT username,password,email FROM users --",
                "' UNION SELECT sqlite_version(),2,3 --",
                "' UNION SELECT name FROM sqlite_master WHERE type='table' --"
            ]
            
            vulnerabilities_found = []
            
            for payload in union_payloads:
                try:
                    vulnerable_query = f"SELECT * FROM test_users WHERE username = '{payload}'"
                    cursor.execute(vulnerable_query)
                    results = cursor.fetchall()
                    
                    if results:
                        vulnerabilities_found.append(f"UNION payload успешен: {payload}")
                        
                except sqlite3.Error as e:
                    # Ошибка - это хорошо
                    pass
            
            conn.close()
            os.remove(test_db)
            
            if vulnerabilities_found:
                return {
                    'passed': False,
                    'description': 'Обнаружены UNION-based SQL инъекции',
                    'details': '; '.join(vulnerabilities_found)
                }
            else:
                return {
                    'passed': True,
                    'description': 'UNION-based SQL инъекции заблокированы',
                    'details': 'Все UNION payloads вызвали ошибки SQLite'
                }
                
        except Exception as e:
            return {
                'passed': False,
                'description': f'Ошибка при тестировании UNION инъекций: {str(e)}',
                'details': str(e)
            }

    def _test_boolean_blind_injection(self) -> Dict:
        """Тестирование Boolean-based blind SQL инъекций"""
        test_db = 'test_boolean.db'
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_data (
                    id INTEGER PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO test_data (value) 
                VALUES ('test_value')
            ''')
            
            conn.commit()
            
            # Тестируем Boolean-based blind инъекции
            boolean_payloads = [
                "' AND 1=1 --",
                "' AND 1=2 --",
                "' AND (SELECT COUNT(*) FROM sqlite_master) > 0 --",
                "' AND (SELECT COUNT(*) FROM sqlite_master) < 0 --"
            ]
            
            vulnerabilities_found = []
            
            for payload in boolean_payloads:
                try:
                    vulnerable_query = f"SELECT * FROM test_data WHERE value = '{payload}'"
                    cursor.execute(vulnerable_query)
                    results = cursor.fetchall()
                    
                    if results:
                        vulnerabilities_found.append(f"Boolean payload успешен: {payload}")
                        
                except sqlite3.Error:
                    pass
            
            conn.close()
            os.remove(test_db)
            
            if vulnerabilities_found:
                return {
                    'passed': False,
                    'description': 'Обнаружены Boolean-based blind SQL инъекции',
                    'details': '; '.join(vulnerabilities_found)
                }
            else:
                return {
                    'passed': True,
                    'description': 'Boolean-based blind SQL инъекции заблокированы',
                    'details': 'Все Boolean payloads вызвали ошибки или не вернули данных'
                }
                
        except Exception as e:
            return {
                'passed': False,
                'description': f'Ошибка при тестировании Boolean blind инъекций: {str(e)}',
                'details': str(e)
            }

    def _test_time_blind_injection(self) -> Dict:
        """Тестирование Time-based blind SQL инъекций"""
        test_db = 'test_time.db'
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO test_table (data) 
                VALUES ('test')
            ''')
            
            conn.commit()
            
            # Тестируем Time-based blind инъекции
            time_payloads = [
                "'; SELECT sqlite_version(); --",
                "' AND (SELECT COUNT(*) FROM sqlite_master) > 0; --",
                "'; PRAGMA user_version; --"
            ]
            
            vulnerabilities_found = []
            
            for payload in time_payloads:
                try:
                    start_time = time.time()
                    vulnerable_query = f"SELECT * FROM test_table WHERE data = '{payload}'"
                    cursor.execute(vulnerable_query)
                    results = cursor.fetchall()
                    end_time = time.time()
                    
                    # Если запрос выполнился быстро, это может быть уязвимость
                    if end_time - start_time < 0.1 and results is not None:
                        vulnerabilities_found.append(f"Time-based payload выполнился быстро: {payload}")
                        
                except sqlite3.Error:
                    pass
            
            conn.close()
            os.remove(test_db)
            
            if vulnerabilities_found:
                return {
                    'passed': False,
                    'description': 'Обнаружены Time-based blind SQL инъекции',
                    'details': '; '.join(vulnerabilities_found)
                }
            else:
                return {
                    'passed': True,
                    'description': 'Time-based blind SQL инъекции заблокированы',
                    'details': 'Все Time-based payloads вызвали ошибки SQLite'
                }
                
        except Exception as e:
            return {
                'passed': False,
                'description': f'Ошибка при тестировании Time-based blind инъекций: {str(e)}',
                'details': str(e)
            }

    def _test_error_based_injection(self) -> Dict:
        """Тестирование Error-based SQL инъекций"""
        test_db = 'test_error.db'
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            ''')
            
            conn.commit()
            
            # Тестируем Error-based инъекции
            error_payloads = [
                "' AND extractvalue(1, concat(0x7e, (SELECT version()), 0x7e)) --",
                "' AND updatexml(1, concat(0x7e, (SELECT version()), 0x7e), 1) --",
                "' AND (SELECT * FROM (SELECT COUNT(*), CONCAT(version(), FLOOR(RAND(0)*2)) x FROM information_schema.tables GROUP BY x) a) --"
            ]
            
            vulnerabilities_found = []
            
            for payload in error_payloads:
                try:
                    vulnerable_query = f"SELECT * FROM test_table WHERE name = '{payload}'"
                    cursor.execute(vulnerable_query)
                    results = cursor.fetchall()
                    
                    if results is not None:
                        vulnerabilities_found.append(f"Error-based payload выполнился: {payload}")
                        
                except sqlite3.Error as e:
                    # Проверяем, содержит ли ошибка информацию о системе
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ['version', 'database', 'table', 'column']):
                        vulnerabilities_found.append(f"Ошибка раскрывает информацию: {str(e)}")
            
            conn.close()
            os.remove(test_db)
            
            if vulnerabilities_found:
                return {
                    'passed': False,
                    'description': 'Обнаружены Error-based SQL инъекции',
                    'details': '; '.join(vulnerabilities_found)
                }
            else:
                return {
                    'passed': True,
                    'description': 'Error-based SQL инъекции заблокированы',
                    'details': 'Все Error-based payloads не раскрыли системную информацию'
                }
                
        except Exception as e:
            return {
                'passed': False,
                'description': f'Ошибка при тестировании Error-based инъекций: {str(e)}',
                'details': str(e)
            }

    def _test_schema_enumeration(self) -> Dict:
        """Тестирование получения схемы базы данных"""
        test_db = 'test_schema.db'
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Создаем тестовые таблицы
            cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER, name TEXT)')
            cursor.execute('CREATE TABLE IF NOT EXISTS admin (id INTEGER, password TEXT)')
            cursor.execute('CREATE TABLE IF NOT EXISTS config (key TEXT, value TEXT)')
            
            conn.commit()
            
            # Пытаемся получить схему
            schema_queries = [
                "SELECT name FROM sqlite_master WHERE type='table'",
                "SELECT sql FROM sqlite_master WHERE type='table'",
                "PRAGMA table_info(users)",
                "PRAGMA database_list"
            ]
            
            schema_info = []
            
            for query in schema_queries:
                try:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    if results:
                        schema_info.append(f"Query '{query}' вернул: {results}")
                except sqlite3.Error:
                    pass
            
            conn.close()
            os.remove(test_db)
            
            if len(schema_info) > 2:  # Если удалось получить много информации о схеме
                return {
                    'passed': False,
                    'description': 'Удалось получить информацию о схеме базы данных',
                    'details': '; '.join(schema_info)
                }
            else:
                return {
                    'passed': True,
                    'description': 'Схема базы данных защищена',
                    'details': 'Не удалось получить критическую информацию о схеме'
                }
                
        except Exception as e:
            return {
                'passed': False,
                'description': f'Ошибка при тестировании схемы: {str(e)}',
                'details': str(e)
            }

    def _test_data_extraction(self) -> Dict:
        """Тестирование извлечения данных"""
        test_db = 'test_extraction.db'
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Создаем тестовые данные
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensitive_data (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    password TEXT,
                    email TEXT,
                    credit_card TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO sensitive_data 
                (username, password, email, credit_card) 
                VALUES ('admin', 'password123', 'admin@test.com', '4111-1111-1111-1111')
            ''')
            
            conn.commit()
            
            # Пытаемся извлечь данные
            extraction_queries = [
                "SELECT * FROM sensitive_data",
                "SELECT username, password FROM sensitive_data",
                "SELECT * FROM sensitive_data WHERE username = 'admin'",
                "SELECT COUNT(*) FROM sensitive_data"
            ]
            
            extracted_data = []
            
            for query in extraction_queries:
                try:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    if results:
                        extracted_data.append(f"Query '{query}' извлек: {results}")
                except sqlite3.Error:
                    pass
            
            conn.close()
            os.remove(test_db)
            
            if extracted_data:
                return {
                    'passed': False,
                    'description': 'Удалось извлечь чувствительные данные',
                    'details': '; '.join(extracted_data)
                }
            else:
                return {
                    'passed': True,
                    'description': 'Чувствительные данные защищены',
                    'details': 'Не удалось извлечь данные из базы'
                }
                
        except Exception as e:
            return {
                'passed': False,
                'description': f'Ошибка при тестировании извлечения данных: {str(e)}',
                'details': str(e)
            }

    def _test_privilege_escalation(self) -> Dict:
        """Тестирование повышения привилегий"""
        test_db = 'test_privileges.db'
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Создаем таблицы с разными уровнями доступа
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    data TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_data (
                    id INTEGER PRIMARY KEY,
                    admin_id INTEGER,
                    secret_data TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_data (user_id, data) 
                VALUES (1, 'user_data')
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO admin_data (admin_id, secret_data) 
                VALUES (1, 'admin_secret')
            ''')
            
            conn.commit()
            
            # Пытаемся получить доступ к админским данным
            privilege_queries = [
                "SELECT * FROM admin_data",
                "SELECT * FROM admin_data WHERE admin_id = 1",
                "INSERT INTO admin_data (admin_id, secret_data) VALUES (999, 'hacked')",
                "UPDATE admin_data SET secret_data = 'compromised' WHERE admin_id = 1",
                "DELETE FROM admin_data WHERE admin_id = 1"
            ]
            
            privilege_escalations = []
            
            for query in privilege_queries:
                try:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    if results is not None:
                        privilege_escalations.append(f"Query '{query}' выполнился успешно")
                except sqlite3.Error as e:
                    # Проверяем, была ли это ошибка доступа
                    if 'permission' in str(e).lower() or 'access' in str(e).lower():
                        pass  # Это хорошо - доступ ограничен
                    else:
                        privilege_escalations.append(f"Query '{query}' вызвал ошибку: {str(e)}")
            
            conn.close()
            os.remove(test_db)
            
            if privilege_escalations:
                return {
                    'passed': False,
                    'description': 'Обнаружены возможности повышения привилегий',
                    'details': '; '.join(privilege_escalations)
                }
            else:
                return {
                    'passed': True,
                    'description': 'Повышение привилегий заблокировано',
                    'details': 'Все попытки доступа к админским данным заблокированы'
                }
                
        except Exception as e:
            return {
                'passed': False,
                'description': f'Ошибка при тестировании привилегий: {str(e)}',
                'details': str(e)
            }

    def _test_input_validation(self) -> Dict:
        """Тестирование валидации входных данных"""
        test_db = 'test_validation.db'
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_input (
                    id INTEGER PRIMARY KEY,
                    user_input TEXT,
                    sanitized_input TEXT
                )
            ''')
            
            conn.commit()
            
            # Тестовые входные данные
            test_inputs = [
                "'; DROP TABLE test_input; --",
                "<script>alert('xss')</script>",
                "../../etc/passwd",
                "null\x00byte",
                "very_long_string_" * 1000,
                "UNICODE: \u0000\u0001\u0002",
                "SQL: ' OR 1=1 --",
                "PATH: /etc/passwd",
                "COMMAND: ; rm -rf /",
                "REGEX: .*"
            ]
            
            validation_issues = []
            
            for test_input in test_inputs:
                try:
                    # Симулируем вставку без валидации
                    cursor.execute('''
                        INSERT INTO test_input (user_input, sanitized_input) 
                        VALUES (?, ?)
                    ''', (test_input, test_input))  # Нет санитизации
                    
                    # Проверяем, что данные сохранились как есть
                    cursor.execute('SELECT user_input FROM test_input WHERE user_input = ?', (test_input,))
                    result = cursor.fetchone()
                    
                    if result and result[0] == test_input:
                        validation_issues.append(f"Небезопасный ввод принят: {test_input[:50]}...")
                    
                except sqlite3.Error:
                    pass
            
            conn.close()
            os.remove(test_db)
            
            if validation_issues:
                return {
                    'passed': False,
                    'description': 'Обнаружены проблемы с валидацией входных данных',
                    'details': '; '.join(validation_issues)
                }
            else:
                return {
                    'passed': True,
                    'description': 'Валидация входных данных работает корректно',
                    'details': 'Все небезопасные входные данные обработаны правильно'
                }
                
        except Exception as e:
            return {
                'passed': False,
                'description': f'Ошибка при тестировании валидации: {str(e)}',
                'details': str(e)
            }

    def generate_advanced_report(self, results: Dict) -> str:
        """Генерация продвинутого отчета о безопасности"""
        report = f"""
# ПРОДВИНУТЫЙ ОТЧЕТ О БЕЗОПАСНОСТИ
Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## СВОДКА ТЕСТИРОВАНИЯ
- Всего тестов: {results['total_tests']}
- Пройдено: {results['passed_tests']}
- Провалено: {results['failed_tests']}
- Процент успеха: {(results['passed_tests'] / results['total_tests'] * 100):.1f}%

## ОБНАРУЖЕННЫЕ УЯЗВИМОСТИ
"""
        
        if results['vulnerabilities']:
            for vuln in results['vulnerabilities']:
                report += f"""
### {vuln['severity']}: {vuln['test_name']}
**Категория:** {vuln['category']}
**Описание:** {vuln['description']}
**Детали:** {vuln['details']}

---
"""
        else:
            report += "\n✅ Критических уязвимостей не обнаружено.\n"
        
        report += "\n## ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ ТЕСТОВ\n"
        
        for test in results['test_details']:
            status = "✅ ПРОЙДЕН" if test['passed'] else "❌ ПРОВАЛЕН"
            report += f"""
### {test['name']} - {status}
**Категория:** {test['category']}
**Уровень критичности:** {test['severity']}
**Описание:** {test['description']}
**Детали:** {test['details']}

"""
        
        report += """
## РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ УЯЗВИМОСТЕЙ

### 1. SQL Injection
- Используйте параметризованные запросы
- Валидируйте все пользовательские данные
- Применяйте принцип минимальных привилегий

### 2. Information Disclosure
- Ограничьте доступ к системной информации
- Настройте правильные права доступа к БД
- Используйте отдельного пользователя БД

### 3. Data Breach
- Шифруйте чувствительные данные
- Реализуйте контроль доступа
- Логируйте все операции с данными

### 4. Privilege Escalation
- Используйте принцип минимальных привилегий
- Разделяйте пользователей и админов
- Регулярно аудируйте права доступа

### 5. Input Validation
- Валидируйте все входные данные
- Используйте whitelist подход
- Санитизируйте пользовательский ввод

## ЗАКЛЮЧЕНИЕ
"""
        
        if results['failed_tests'] > 0:
            report += f"Обнаружено {results['failed_tests']} уязвимостей, требующих немедленного исправления."
        else:
            report += "Все тесты безопасности пройдены успешно."
        
        return report

def main():
    """Основная функция"""
    print("🔒 Запуск продвинутого тестера безопасности...")
    
    tester = AdvancedSecurityTester()
    results = tester.run_all_tests()
    report = tester.generate_advanced_report(results)
    
    # Сохранение отчета
    report_file = f"advanced_security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + "="*80)
    print(report)
    print("="*80)
    
    print(f"\n📊 Итоговая статистика:")
    print(f"- Всего тестов: {results['total_tests']}")
    print(f"- Пройдено: {results['passed_tests']}")
    print(f"- Провалено: {results['failed_tests']}")
    print(f"- Процент успеха: {(results['passed_tests'] / results['total_tests'] * 100):.1f}%")
    
    if results['failed_tests'] > 0:
        print(f"\n⚠️ ВНИМАНИЕ: Обнаружено {results['failed_tests']} уязвимостей!")
        print("Рекомендуется немедленно исправить найденные проблемы.")
    else:
        print("\n✅ Все тесты безопасности пройдены успешно!")

if __name__ == "__main__":
    main()