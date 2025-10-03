#!/usr/bin/env python3
"""
Руководство по исправлению уязвимостей безопасности
Содержит конкретные рекомендации и примеры кода для устранения найденных проблем
"""

import os
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SecurityFix:
    """Исправление уязвимости"""
    vulnerability_type: str
    severity: str
    description: str
    current_code: str
    fixed_code: str
    explanation: str
    additional_recommendations: List[str]

class SecurityFixesGuide:
    """Руководство по исправлению уязвимостей"""
    
    def __init__(self):
        self.fixes = self._initialize_fixes()
    
    def _initialize_fixes(self) -> List[SecurityFix]:
        """Инициализация исправлений"""
        return [
            SecurityFix(
                vulnerability_type="SQL Injection",
                severity="CRITICAL",
                description="Использование параметризованных запросов",
                current_code="""
# ❌ УЯЗВИМЫЙ КОД
user_input = "'; DROP TABLE clients; --"
query = f"SELECT * FROM clients WHERE name = '{user_input}'"
cursor.execute(query)
                """,
                fixed_code="""
# ✅ БЕЗОПАСНЫЙ КОД
user_input = "'; DROP TABLE clients; --"
query = "SELECT * FROM clients WHERE name = ?"
cursor.execute(query, (user_input,))
                """,
                explanation="Параметризованные запросы предотвращают SQL-инъекции, так как пользовательский ввод обрабатывается как данные, а не как код SQL.",
                additional_recommendations=[
                    "Всегда используйте плейсхолдеры (?) для пользовательских данных",
                    "Никогда не используйте f-строки или .format() для SQL-запросов",
                    "Валидируйте входные данные перед использованием в запросах"
                ]
            ),
            
            SecurityFix(
                vulnerability_type="Input Validation",
                severity="HIGH",
                description="Валидация и санитизация пользовательского ввода",
                current_code="""
# ❌ УЯЗВИМЫЙ КОД
def save_user_data(user_input):
    # Нет валидации
    cursor.execute("INSERT INTO users (data) VALUES (?)", (user_input,))
                """,
                fixed_code="""
# ✅ БЕЗОПАСНЫЙ КОД
import re
import html

def validate_input(user_input):
    # Проверка длины
    if len(user_input) > 1000:
        raise ValueError("Input too long")
    
    # Удаление опасных символов
    user_input = re.sub(r'[<>"\']', '', user_input)
    
    # HTML-экранирование
    user_input = html.escape(user_input)
    
    return user_input

def save_user_data(user_input):
    validated_input = validate_input(user_input)
    cursor.execute("INSERT INTO users (data) VALUES (?)", (validated_input,))
                """,
                explanation="Валидация входных данных предотвращает различные типы атак, включая XSS, SQL-инъекции и инъекции команд.",
                additional_recommendations=[
                    "Используйте whitelist подход для валидации",
                    "Ограничивайте длину входных данных",
                    "Экранируйте специальные символы",
                    "Используйте регулярные выражения для проверки формата"
                ]
            ),
            
            SecurityFix(
                vulnerability_type="Database Access Control",
                severity="CRITICAL",
                description="Ограничение доступа к базе данных",
                current_code="""
# ❌ УЯЗВИМЫЙ КОД
# Все пользователи имеют полный доступ к БД
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM admin_users")  # Любой может получить админские данные
                """,
                fixed_code="""
# ✅ БЕЗОПАСНЫЙ КОД
import sqlite3
from functools import wraps

class DatabaseManager:
    def __init__(self, db_path, user_role='user'):
        self.db_path = db_path
        self.user_role = user_role
    
    def check_permission(self, operation, table):
        """Проверка прав доступа"""
        if self.user_role == 'admin':
            return True
        elif self.user_role == 'user':
            # Пользователи могут только читать свои данные
            return operation == 'SELECT' and table in ['user_data', 'public_data']
        return False
    
    def execute_query(self, query, params=None):
        """Безопасное выполнение запроса с проверкой прав"""
        # Парсим запрос для определения операции и таблицы
        query_upper = query.upper().strip()
        operation = query_upper.split()[0]
        
        # Извлекаем имя таблицы (упрощенная версия)
        if 'FROM' in query_upper:
            table = query_upper.split('FROM')[1].split()[0]
        elif 'INTO' in query_upper:
            table = query_upper.split('INTO')[1].split()[0]
        else:
            table = 'unknown'
        
        if not self.check_permission(operation, table):
            raise PermissionError(f"Access denied for {operation} on {table}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        result = cursor.fetchall()
        conn.close()
        return result

# Использование
db = DatabaseManager('database.db', user_role='user')
# db.execute_query("SELECT * FROM admin_users")  # Вызовет PermissionError
                """,
                explanation="Контроль доступа к базе данных предотвращает несанкционированный доступ к чувствительным данным.",
                additional_recommendations=[
                    "Создайте отдельного пользователя БД с ограниченными правами",
                    "Используйте принцип минимальных привилегий",
                    "Реализуйте ролевую модель доступа",
                    "Логируйте все операции с базой данных"
                ]
            ),
            
            SecurityFix(
                vulnerability_type="Error Handling",
                severity="MEDIUM",
                description="Безопасная обработка ошибок",
                current_code="""
# ❌ УЯЗВИМЫЙ КОД
try:
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
except Exception as e:
    # Раскрывает внутреннюю информацию
    return f"Error: {str(e)}"
                """,
                fixed_code="""
# ✅ БЕЗОПАСНЫЙ КОД
import logging

logger = logging.getLogger(__name__)

def get_user_data(user_id):
    try:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        return result
    except sqlite3.Error as e:
        # Логируем детальную ошибку для администраторов
        logger.error(f"Database error for user {user_id}: {str(e)}")
        # Возвращаем общее сообщение пользователю
        return None
    except Exception as e:
        # Логируем неожиданные ошибки
        logger.critical(f"Unexpected error for user {user_id}: {str(e)}")
        return None
                """,
                explanation="Безопасная обработка ошибок предотвращает раскрытие внутренней информации системы.",
                additional_recommendations=[
                    "Логируйте детальные ошибки для администраторов",
                    "Возвращайте общие сообщения пользователям",
                    "Не раскрывайте пути к файлам или структуру БД",
                    "Используйте разные уровни логирования"
                ]
            ),
            
            SecurityFix(
                vulnerability_type="Data Encryption",
                severity="HIGH",
                description="Шифрование чувствительных данных",
                current_code="""
# ❌ УЯЗВИМЫЙ КОД
# Чувствительные данные хранятся в открытом виде
cursor.execute("INSERT INTO users (password, credit_card) VALUES (?, ?)", 
               (password, credit_card))
                """,
                fixed_code="""
# ✅ БЕЗОПАСНЫЙ КОД
import hashlib
import secrets
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key=None):
        if key is None:
            key = Fernet.generate_key()
        self.cipher = Fernet(key)
    
    def hash_password(self, password):
        """Хеширование пароля с солью"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                          password.encode('utf-8'), 
                                          salt.encode('utf-8'), 
                                          100000)
        return f"{salt}:{password_hash.hex()}"
    
    def encrypt_data(self, data):
        """Шифрование данных"""
        return self.cipher.encrypt(data.encode('utf-8'))
    
    def decrypt_data(self, encrypted_data):
        """Расшифровка данных"""
        return self.cipher.decrypt(encrypted_data).decode('utf-8')

# Использование
encryption = DataEncryption()

# Хеширование пароля
hashed_password = encryption.hash_password("user_password")

# Шифрование чувствительных данных
encrypted_credit_card = encryption.encrypt_data("4111-1111-1111-1111")

cursor.execute("INSERT INTO users (password, credit_card) VALUES (?, ?)", 
               (hashed_password, encrypted_credit_card))
                """,
                explanation="Шифрование данных защищает чувствительную информацию даже в случае компрометации базы данных.",
                additional_recommendations=[
                    "Используйте сильные алгоритмы хеширования (PBKDF2, bcrypt, Argon2)",
                    "Добавляйте соль к паролям",
                    "Шифруйте персональные данные (PII)",
                    "Храните ключи шифрования отдельно от данных"
                ]
            )
        ]
    
    def generate_fixes_report(self) -> str:
        """Генерация отчета с исправлениями"""
        report = f"""
# РУКОВОДСТВО ПО ИСПРАВЛЕНИЮ УЯЗВИМОСТЕЙ БЕЗОПАСНОСТИ

## ОБЗОР
Этот документ содержит конкретные рекомендации по исправлению найденных уязвимостей в коде бота.

## КРИТИЧЕСКИЕ УЯЗВИМОСТИ (ТРЕБУЮТ НЕМЕДЛЕННОГО ИСПРАВЛЕНИЯ)
"""
        
        critical_fixes = [fix for fix in self.fixes if fix.severity == "CRITICAL"]
        for fix in critical_fixes:
            report += f"""
### {fix.vulnerability_type} - {fix.severity}

**Описание:** {fix.description}

**Текущий уязвимый код:**
```python
{fix.current_code.strip()}
```

**Исправленный код:**
```python
{fix.fixed_code.strip()}
```

**Объяснение:** {fix.explanation}

**Дополнительные рекомендации:**
"""
            for rec in fix.additional_recommendations:
                report += f"- {rec}\n"
            
            report += "\n---\n"
        
        report += """
## ВЫСОКИЙ УРОВЕНЬ РИСКА
"""
        
        high_fixes = [fix for fix in self.fixes if fix.severity == "HIGH"]
        for fix in high_fixes:
            report += f"""
### {fix.vulnerability_type} - {fix.severity}

**Описание:** {fix.description}

**Текущий уязвимый код:**
```python
{fix.current_code.strip()}
```

**Исправленный код:**
```python
{fix.fixed_code.strip()}
```

**Объяснение:** {fix.explanation}

**Дополнительные рекомендации:**
"""
            for rec in fix.additional_recommendations:
                report += f"- {rec}\n"
            
            report += "\n---\n"
        
        report += """
## СРЕДНИЙ УРОВЕНЬ РИСКА
"""
        
        medium_fixes = [fix for fix in self.fixes if fix.severity == "MEDIUM"]
        for fix in medium_fixes:
            report += f"""
### {fix.vulnerability_type} - {fix.severity}

**Описание:** {fix.description}

**Текущий уязвимый код:**
```python
{fix.current_code.strip()}
```

**Исправленный код:**
```python
{fix.fixed_code.strip()}
```

**Объяснение:** {fix.explanation}

**Дополнительные рекомендации:**
"""
            for rec in fix.additional_recommendations:
                report += f"- {rec}\n"
            
            report += "\n---\n"
        
        report += """
## ПЛАН ДЕЙСТВИЙ ПО ИСПРАВЛЕНИЮ

### Немедленные действия (в течение 24 часов):
1. **Исправить все SQL-инъекции** - заменить строковую конкатенацию на параметризованные запросы
2. **Реализовать контроль доступа** - ограничить права пользователей БД
3. **Добавить валидацию входных данных** - проверить все пользовательские вводы

### Краткосрочные действия (в течение недели):
1. **Шифрование чувствительных данных** - зашифровать пароли и персональные данные
2. **Улучшить обработку ошибок** - скрыть внутреннюю информацию от пользователей
3. **Добавить логирование** - записывать все операции с БД

### Долгосрочные действия (в течение месяца):
1. **Регулярное тестирование безопасности** - автоматизировать проверки
2. **Обновление зависимостей** - поддерживать актуальные версии библиотек
3. **Обучение команды** - повысить осведомленность о безопасности

## ИНСТРУМЕНТЫ ДЛЯ АВТОМАТИЗАЦИИ

### 1. Статический анализ кода:
```bash
# Установка bandit для Python
pip install bandit

# Проверка кода на уязвимости
bandit -r . -f json -o security_report.json
```

### 2. Тестирование на проникновение:
```bash
# Установка sqlmap для тестирования SQL-инъекций
pip install sqlmap

# Тестирование веб-приложения
sqlmap -u "http://your-app.com/api" --batch
```

### 3. Мониторинг безопасности:
```python
# Пример логирования подозрительной активности
import logging

security_logger = logging.getLogger('security')

def log_suspicious_activity(user_id, action, details):
    security_logger.warning(f"Suspicious activity: User {user_id}, Action: {action}, Details: {details}")
```

## ЗАКЛЮЧЕНИЕ

Безопасность - это не одноразовое мероприятие, а непрерывный процесс. Регулярно:
- Проводите аудиты безопасности
- Обновляйте зависимости
- Тестируйте на уязвимости
- Обучайте команду
- Мониторьте подозрительную активность

Помните: лучше предотвратить атаку, чем устранять её последствия.
"""
        
        return report
    
    def apply_fixes_to_code(self) -> Dict[str, str]:
        """Применение исправлений к реальному коду"""
        fixes_applied = {}
        
        # Исправление в prompt_ab_testing.py
        fixes_applied['prompt_ab_testing.py'] = """
# Исправление в функции get_test_statistics
# Заменить строковую конкатенацию на безопасное формирование запроса

def get_test_statistics(self, prompt_type: Optional[PromptType] = None) -> Dict:
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    # Базовый запрос
    base_query = '''
        SELECT 
            r.prompt_variant_id,
            p.name,
            COUNT(*) as total_uses,
            AVG(r.user_feedback) as avg_feedback,
            AVG(r.response_quality) as avg_quality,
            AVG(r.user_engagement) as avg_engagement,
            SUM(CASE WHEN r.conversion = 1 THEN 1 ELSE 0 END) as conversions,
            CAST(SUM(CASE WHEN r.conversion = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as conversion_rate
        FROM ab_test_results r
        JOIN prompt_variants p ON r.prompt_variant_id = p.id
    '''
    
    # Безопасное формирование запроса
    if prompt_type:
        full_query = base_query + ' WHERE r.prompt_type = ? GROUP BY r.prompt_variant_id'
        cursor.execute(full_query, (prompt_type.value,))
    else:
        full_query = base_query + ' GROUP BY r.prompt_variant_id'
        cursor.execute(full_query)
    
    results = cursor.fetchall()
    # ... остальной код
"""
        
        # Добавление валидации входных данных
        fixes_applied['input_validation.py'] = """
# Новый модуль для валидации входных данных

import re
import html
from typing import Optional

class InputValidator:
    def __init__(self):
        self.max_length = 1000
        self.allowed_patterns = {
            'name': r'^[a-zA-Zа-яА-ЯёЁ\s\-\.]{1,100}$',
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'telegram_id': r'^\d{1,20}$'
        }
    
    def validate_text(self, text: str, field_type: str = 'general') -> Optional[str]:
        if not text or not isinstance(text, str):
            return None
        
        # Проверка длины
        if len(text) > self.max_length:
            raise ValueError(f"Input too long. Maximum {self.max_length} characters allowed.")
        
        # HTML-экранирование
        text = html.escape(text)
        
        # Удаление опасных символов
        text = re.sub(r'[<>"\']', '', text)
        
        # Проверка по типу поля
        if field_type in self.allowed_patterns:
            if not re.match(self.allowed_patterns[field_type], text):
                raise ValueError(f"Invalid format for {field_type}")
        
        return text
    
    def validate_telegram_id(self, telegram_id) -> int:
        try:
            telegram_id = int(telegram_id)
            if telegram_id <= 0:
                raise ValueError("Telegram ID must be positive")
            return telegram_id
        except (ValueError, TypeError):
            raise ValueError("Invalid Telegram ID format")

# Использование в основном коде
validator = InputValidator()

def save_analysis(telegram_id: int, name: str, analysis_type: str, analysis_data: dict, payment_status: str = 'free'):
    # Валидация входных данных
    telegram_id = validator.validate_telegram_id(telegram_id)
    name = validator.validate_text(name, 'name')
    analysis_type = validator.validate_text(analysis_type)
    
    # Остальной код...
"""
        
        return fixes_applied

def main():
    """Основная функция"""
    print("🔧 Генерация руководства по исправлению уязвимостей...")
    
    guide = SecurityFixesGuide()
    report = guide.generate_fixes_report()
    
    # Сохранение отчета
    report_file = "security_fixes_guide.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Руководство сохранено в файл: {report_file}")
    
    # Применение исправлений
    fixes = guide.apply_fixes_to_code()
    
    print("\n📝 Примеры исправлений для файлов:")
    for filename, fix_code in fixes.items():
        print(f"\n{filename}:")
        print(fix_code[:200] + "..." if len(fix_code) > 200 else fix_code)
    
    print(f"\n📊 Статистика:")
    print(f"- Всего исправлений: {len(guide.fixes)}")
    print(f"- Критических: {len([f for f in guide.fixes if f.severity == 'CRITICAL'])}")
    print(f"- Высокого уровня: {len([f for f in guide.fixes if f.severity == 'HIGH'])}")
    print(f"- Среднего уровня: {len([f for f in guide.fixes if f.severity == 'MEDIUM'])}")

if __name__ == "__main__":
    main()