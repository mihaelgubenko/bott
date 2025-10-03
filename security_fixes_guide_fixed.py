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
                current_code="# УЯЗВИМЫЙ КОД\nuser_input = \"'; DROP TABLE clients; --\"\nquery = f\"SELECT * FROM clients WHERE name = '{user_input}'\"\ncursor.execute(query)",
                fixed_code="# БЕЗОПАСНЫЙ КОД\nuser_input = \"'; DROP TABLE clients; --\"\nquery = \"SELECT * FROM clients WHERE name = ?\"\ncursor.execute(query, (user_input,))",
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
                current_code="# УЯЗВИМЫЙ КОД\ndef save_user_data(user_input):\n    # Нет валидации\n    cursor.execute(\"INSERT INTO users (data) VALUES (?)\", (user_input,))",
                fixed_code="# БЕЗОПАСНЫЙ КОД\nimport re\nimport html\n\ndef validate_input(user_input):\n    if len(user_input) > 1000:\n        raise ValueError(\"Input too long\")\n    user_input = re.sub(r'[<>\"\\']', '', user_input)\n    user_input = html.escape(user_input)\n    return user_input\n\ndef save_user_data(user_input):\n    validated_input = validate_input(user_input)\n    cursor.execute(\"INSERT INTO users (data) VALUES (?)\", (validated_input,))",
                explanation="Валидация входных данных предотвращает различные типы атак, включая XSS, SQL-инъекции и инъекции команд.",
                additional_recommendations=[
                    "Используйте whitelist подход для валидации",
                    "Ограничивайте длину входных данных",
                    "Экранируйте специальные символы",
                    "Используйте регулярные выражения для проверки формата"
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
        
        for fix in self.fixes:
            report += f"""
### {fix.vulnerability_type} - {fix.severity}

**Описание:** {fix.description}

**Текущий уязвимый код:**
```python
{fix.current_code}
```

**Исправленный код:**
```python
{fix.fixed_code}
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
    
    print(f"\n📊 Статистика:")
    print(f"- Всего исправлений: {len(guide.fixes)}")
    print(f"- Критических: {len([f for f in guide.fixes if f.severity == 'CRITICAL'])}")
    print(f"- Высокого уровня: {len([f for f in guide.fixes if f.severity == 'HIGH'])}")

if __name__ == "__main__":
    main()