#!/usr/bin/env python3
"""
Утилита для тестирования SQL-инъекций и анализа уязвимостей в боте
Проверяет все SQL-запросы на предмет возможных уязвимостей
"""

import sqlite3
import json
import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VulnerabilityReport:
    """Отчет об уязвимости"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    vulnerability_type: str
    location: str
    description: str
    recommendation: str
    code_example: str

@dataclass
class TestResult:
    """Результат теста безопасности"""
    test_name: str
    passed: bool
    details: str
    vulnerability_found: Optional[VulnerabilityReport] = None

class SQLSecurityTester:
    """Тестер безопасности SQL-запросов"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.vulnerabilities = []
        self.test_results = []
        
        # Паттерны для SQL-инъекций
        self.sql_injection_patterns = [
            # Базовые SQL-инъекции
            r"'.*?(union|select|insert|update|delete|drop|create|alter).*?'",
            r"'.*?or.*?'.*?=.*?'",
            r"'.*?and.*?'.*?=.*?'",
            r"'.*?;.*?'",
            r"'.*?--.*?'",
            r"'.*?/\*.*?\*/.*?'",
            
            # Time-based blind SQL injection
            r"'.*?sleep\s*\(.*?\).*?'",
            r"'.*?waitfor.*?delay.*?'",
            r"'.*?benchmark\s*\(.*?\).*?'",
            
            # Boolean-based blind SQL injection
            r"'.*?and\s+1\s*=\s*1.*?'",
            r"'.*?and\s+1\s*=\s*2.*?'",
            r"'.*?or\s+1\s*=\s*1.*?'",
            
            # Error-based SQL injection
            r"'.*?extractvalue\s*\(.*?\).*?'",
            r"'.*?updatexml\s*\(.*?\).*?'",
            r"'.*?exp\s*\(.*?\).*?'",
            
            # Stacked queries
            r"'.*?;\s*(select|insert|update|delete|drop|create).*?'",
        ]
        
        # Опасные функции SQLite
        self.dangerous_functions = [
            'load_extension', 'sqlite_version', 'randomblob', 'zeroblob',
            'changes', 'last_insert_rowid', 'total_changes'
        ]

    def analyze_code_for_vulnerabilities(self) -> List[VulnerabilityReport]:
        """Анализ кода на предмет уязвимостей"""
        vulnerabilities = []
        
        # Анализируем основные файлы
        files_to_analyze = [
            'hr_psychoanalyst_bot.py',
            'prompt_ab_testing.py',
            'clear_memory.py'
        ]
        
        for file_path in files_to_analyze:
            if os.path.exists(file_path):
                file_vulns = self._analyze_file(file_path)
                vulnerabilities.extend(file_vulns)
        
        return vulnerabilities

    def _analyze_file(self, file_path: str) -> List[VulnerabilityReport]:
        """Анализ конкретного файла"""
        vulnerabilities = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Ищем SQL-запросы
            for i, line in enumerate(lines, 1):
                line_vulns = self._analyze_line(line, file_path, i)
                vulnerabilities.extend(line_vulns)
                
        except Exception as e:
            logger.error(f"Ошибка при анализе файла {file_path}: {e}")
        
        return vulnerabilities

    def _analyze_line(self, line: str, file_path: str, line_number: int) -> List[VulnerabilityReport]:
        """Анализ конкретной строки кода"""
        vulnerabilities = []
        
        # Проверяем на использование cursor.execute
        if 'cursor.execute' in line:
            # Проверяем на параметризованные запросы
            if '?' not in line and '%s' not in line and 'format(' not in line:
                # Проверяем на строковую конкатенацию
                if '+' in line or 'f"' in line or 'f\'' in line or '.format(' in line:
                    vuln = VulnerabilityReport(
                        severity="CRITICAL",
                        vulnerability_type="SQL Injection",
                        location=f"{file_path}:{line_number}",
                        description="Обнаружена потенциальная SQL-инъекция через строковую конкатенацию",
                        recommendation="Используйте параметризованные запросы с плейсхолдерами (?)",
                        code_example=line.strip()
                    )
                    vulnerabilities.append(vuln)
        
        # Проверяем на прямые SQL-запросы без параметров
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER']
        for keyword in sql_keywords:
            if keyword in line.upper() and 'cursor.execute' in line:
                # Проверяем, есть ли пользовательский ввод
                if any(var in line for var in ['user_input', 'text', 'message', 'name', 'data']):
                    vuln = VulnerabilityReport(
                        severity="HIGH",
                        vulnerability_type="Potential SQL Injection",
                        location=f"{file_path}:{line_number}",
                        description=f"SQL-запрос с {keyword} может содержать пользовательский ввод",
                        recommendation="Убедитесь, что используется параметризация запросов",
                        code_example=line.strip()
                    )
                    vulnerabilities.append(vuln)
        
        return vulnerabilities

    def test_sql_injection_vectors(self) -> List[TestResult]:
        """Тестирование векторов SQL-инъекций"""
        test_results = []
        
        # Тестовые векторы SQL-инъекций
        injection_vectors = [
            # Базовые инъекции
            "'; DROP TABLE clients; --",
            "' OR '1'='1",
            "' OR 1=1 --",
            "'; INSERT INTO clients VALUES (999, 'hacker', 'test', '{}', 'free', datetime('now')); --",
            
            # Time-based blind injection
            "'; SELECT sqlite_version(); --",
            "' UNION SELECT 1,2,3,4,5,6 --",
            
            # Boolean-based blind injection
            "' AND 1=1 --",
            "' AND 1=2 --",
            
            # Error-based injection
            "'; SELECT load_extension('test'); --",
            
            # Stacked queries
            "'; UPDATE clients SET name='HACKED' WHERE telegram_id=1; --",
        ]
        
        for vector in injection_vectors:
            result = self._test_injection_vector(vector)
            test_results.append(result)
        
        return test_results

    def _test_injection_vector(self, injection_vector: str) -> TestResult:
        """Тестирование конкретного вектора инъекции"""
        try:
            # Создаем тестовую базу данных
            test_db = 'test_security.db'
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Создаем тестовую таблицу
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_clients (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER,
                    name TEXT,
                    data TEXT
                )
            ''')
            
            # Вставляем тестовые данные
            cursor.execute('''
                INSERT OR REPLACE INTO test_clients 
                (telegram_id, name, data) VALUES (?, ?, ?)
            ''', (1, 'test_user', 'test_data'))
            
            conn.commit()
            
            # Тестируем инъекцию
            try:
                # Симулируем уязвимый запрос
                vulnerable_query = f"SELECT * FROM test_clients WHERE name = '{injection_vector}'"
                cursor.execute(vulnerable_query)
                results = cursor.fetchall()
                
                # Если запрос выполнился без ошибок, это может быть уязвимость
                if results is not None:
                    return TestResult(
                        test_name=f"SQL Injection Test: {injection_vector[:30]}...",
                        passed=False,
                        details=f"Запрос выполнился успешно, что может указывать на уязвимость",
                        vulnerability_found=VulnerabilityReport(
                            severity="HIGH",
                            vulnerability_type="SQL Injection",
                            location="Test Environment",
                            description=f"Вектор инъекции '{injection_vector}' выполнился успешно",
                            recommendation="Используйте параметризованные запросы",
                            code_example=vulnerable_query
                        )
                    )
                
            except sqlite3.Error as e:
                # Ошибка SQLite - это хорошо, значит защита работает
                return TestResult(
                    test_name=f"SQL Injection Test: {injection_vector[:30]}...",
                    passed=True,
                    details=f"Запрос вызвал ошибку SQLite: {str(e)[:100]}"
                )
            
            conn.close()
            os.remove(test_db)
            
            return TestResult(
                test_name=f"SQL Injection Test: {injection_vector[:30]}...",
                passed=True,
                details="Тест завершен без обнаружения уязвимости"
            )
            
        except Exception as e:
            return TestResult(
                test_name=f"SQL Injection Test: {injection_vector[:30]}...",
                passed=False,
                details=f"Ошибка при тестировании: {str(e)}"
            )

    def test_parameterized_queries(self) -> List[TestResult]:
        """Тестирование параметризованных запросов"""
        test_results = []
        
        # Тестируем безопасные запросы
        safe_queries = [
            ("SELECT * FROM clients WHERE telegram_id = ?", [12345]),
            ("INSERT INTO clients (telegram_id, name, analysis_type) VALUES (?, ?, ?)", [12345, "test", "express"]),
            ("UPDATE clients SET name = ? WHERE telegram_id = ?", ["new_name", 12345]),
        ]
        
        for query, params in safe_queries:
            result = self._test_parameterized_query(query, params)
            test_results.append(result)
        
        return test_results

    def _test_parameterized_query(self, query: str, params: list) -> TestResult:
        """Тестирование параметризованного запроса"""
        try:
            test_db = 'test_parameterized.db'
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Создаем тестовую таблицу
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_clients (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER,
                    name TEXT,
                    analysis_type TEXT
                )
            ''')
            
            # Вставляем тестовые данные
            cursor.execute('''
                INSERT OR REPLACE INTO test_clients 
                (telegram_id, name, analysis_type) VALUES (?, ?, ?)
            ''', (12345, "test_user", "express"))
            
            conn.commit()
            
            # Выполняем тестовый запрос
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            conn.close()
            os.remove(test_db)
            
            return TestResult(
                test_name=f"Parameterized Query Test: {query[:50]}...",
                passed=True,
                details="Параметризованный запрос выполнен успешно"
            )
            
        except Exception as e:
            return TestResult(
                test_name=f"Parameterized Query Test: {query[:50]}...",
                passed=False,
                details=f"Ошибка при тестировании: {str(e)}"
            )

    def generate_security_report(self) -> str:
        """Генерация отчета о безопасности"""
        vulnerabilities = self.analyze_code_for_vulnerabilities()
        injection_tests = self.test_sql_injection_vectors()
        parameterized_tests = self.test_parameterized_queries()
        
        report = f"""
# ОТЧЕТ О БЕЗОПАСНОСТИ SQL-ЗАПРОСОВ
Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## СВОДКА
- Найдено уязвимостей: {len(vulnerabilities)}
- Критических: {len([v for v in vulnerabilities if v.severity == 'CRITICAL'])}
- Высокого уровня: {len([v for v in vulnerabilities if v.severity == 'HIGH'])}
- Среднего уровня: {len([v for v in vulnerabilities if v.severity == 'MEDIUM'])}
- Низкого уровня: {len([v for v in vulnerabilities if v.severity == 'LOW'])}

## НАЙДЕННЫЕ УЯЗВИМОСТИ
"""
        
        for vuln in vulnerabilities:
            report += f"""
### {vuln.severity}: {vuln.vulnerability_type}
**Местоположение:** {vuln.location}
**Описание:** {vuln.description}
**Рекомендация:** {vuln.recommendation}
**Код:**
```python
{vuln.code_example}
```

---
"""
        
        report += "\n## РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ SQL-ИНЪЕКЦИЙ\n"
        
        for test in injection_tests:
            status = "✅ ПРОЙДЕН" if test.passed else "❌ ПРОВАЛЕН"
            report += f"- {test.test_name}: {status}\n"
            report += f"  Детали: {test.details}\n"
            if test.vulnerability_found:
                report += f"  ⚠️ Уязвимость: {test.vulnerability_found.description}\n"
        
        report += "\n## РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ПАРАМЕТРИЗОВАННЫХ ЗАПРОСОВ\n"
        
        for test in parameterized_tests:
            status = "✅ ПРОЙДЕН" if test.passed else "❌ ПРОВАЛЕН"
            report += f"- {test.test_name}: {status}\n"
            report += f"  Детали: {test.details}\n"
        
        report += f"""

## РЕКОМЕНДАЦИИ ПО БЕЗОПАСНОСТИ

1. **Используйте параметризованные запросы:**
   ```python
   # ✅ Безопасно
   cursor.execute('SELECT * FROM clients WHERE telegram_id = ?', (user_id,))
   
   # ❌ Опасно
   cursor.execute(f'SELECT * FROM clients WHERE telegram_id = 12345')
   ```

2. **Валидация входных данных:**
   - Проверяйте все пользовательские данные
   - Используйте whitelist для разрешенных значений
   - Ограничивайте длину входных данных

3. **Принцип минимальных привилегий:**
   - Используйте отдельного пользователя БД с ограниченными правами
   - Не используйте root/административные права

4. **Логирование и мониторинг:**
   - Логируйте все SQL-запросы
   - Мониторьте подозрительную активность
   - Настройте алерты на аномальные запросы

5. **Регулярное тестирование:**
   - Проводите регулярные тесты на проникновение
   - Используйте автоматизированные инструменты
   - Обновляйте зависимости

## ЗАКЛЮЧЕНИЕ
"""
        
        if vulnerabilities:
            report += f"Обнаружено {len(vulnerabilities)} уязвимостей, требующих немедленного исправления."
        else:
            report += "Критических уязвимостей не обнаружено, но рекомендуется регулярное тестирование."
        
        return report

    def run_full_security_audit(self) -> str:
        """Запуск полного аудита безопасности"""
        logger.info("Запуск полного аудита безопасности SQL-запросов...")
        
        # Анализ кода
        logger.info("Анализ кода на предмет уязвимостей...")
        vulnerabilities = self.analyze_code_for_vulnerabilities()
        
        # Тестирование SQL-инъекций
        logger.info("Тестирование векторов SQL-инъекций...")
        injection_tests = self.test_sql_injection_vectors()
        
        # Тестирование параметризованных запросов
        logger.info("Тестирование параметризованных запросов...")
        parameterized_tests = self.test_parameterized_queries()
        
        # Генерация отчета
        logger.info("Генерация отчета...")
        report = self.generate_security_report()
        
        # Сохранение отчета
        report_file = f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Отчет сохранен в файл: {report_file}")
        
        return report

def main():
    """Основная функция"""
    print("🔒 Запуск тестера безопасности SQL-запросов...")
    
    tester = SQLSecurityTester()
    report = tester.run_full_security_audit()
    
    print("\n" + "="*80)
    print(report)
    print("="*80)
    
    print(f"\n📊 Статистика:")
    vulnerabilities = tester.analyze_code_for_vulnerabilities()
    critical_count = len([v for v in vulnerabilities if v.severity == 'CRITICAL'])
    high_count = len([v for v in vulnerabilities if v.severity == 'HIGH'])
    
    print(f"- Всего уязвимостей: {len(vulnerabilities)}")
    print(f"- Критических: {critical_count}")
    print(f"- Высокого уровня: {high_count}")
    
    if critical_count > 0 or high_count > 0:
        print("\n⚠️ ВНИМАНИЕ: Обнаружены критические уязвимости!")
        print("Рекомендуется немедленно исправить найденные проблемы.")
    else:
        print("\n✅ Критических уязвимостей не обнаружено.")

if __name__ == "__main__":
    main()