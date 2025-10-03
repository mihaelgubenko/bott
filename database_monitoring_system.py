#!/usr/bin/env python3
"""
Система мониторинга базы данных и алертинга
Отслеживает производительность, безопасность и доступность БД
"""

import sqlite3
import time
import json
import logging
import threading
import smtplib
import requests
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import psutil
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseMetrics:
    """Метрики базы данных"""
    timestamp: datetime
    connection_count: int
    active_queries: int
    slow_queries: int
    error_count: int
    cache_hit_rate: float
    disk_usage_mb: float
    memory_usage_mb: float
    cpu_usage_percent: float
    response_time_ms: float

@dataclass
class AlertRule:
    """Правило алертинга"""
    name: str
    metric: str
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    threshold: float
    severity: str  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    enabled: bool = True
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None

@dataclass
class Alert:
    """Алерт"""
    rule_name: str
    severity: str
    message: str
    timestamp: datetime
    metric_value: float
    threshold: float
    details: Dict[str, Any] = None

class DatabaseMonitoringSystem:
    """Система мониторинга базы данных"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.metrics_history = deque(maxlen=1000)  # Храним последние 1000 метрик
        self.alerts = deque(maxlen=500)  # Храним последние 500 алертов
        self.alert_rules = {}
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Настройки алертинга
        self.alert_config = {
            'email_enabled': False,
            'email_smtp_server': 'smtp.gmail.com',
            'email_smtp_port': 587,
            'email_username': '',
            'email_password': '',
            'email_recipients': [],
            'webhook_enabled': False,
            'webhook_url': '',
            'slack_enabled': False,
            'slack_webhook_url': ''
        }
        
        # Инициализация правил алертинга
        self._init_default_alert_rules()
        
        # Инициализация БД для хранения метрик
        self._init_monitoring_database()
    
    def _init_default_alert_rules(self):
        """Инициализация правил алертинга по умолчанию"""
        default_rules = [
            AlertRule(
                name="High CPU Usage",
                metric="cpu_usage_percent",
                operator=">",
                threshold=80.0,
                severity="WARNING",
                cooldown_minutes=5
            ),
            AlertRule(
                name="High Memory Usage",
                metric="memory_usage_mb",
                operator=">",
                threshold=1000.0,
                severity="WARNING",
                cooldown_minutes=10
            ),
            AlertRule(
                name="High Disk Usage",
                metric="disk_usage_mb",
                operator=">",
                threshold=500.0,
                severity="ERROR",
                cooldown_minutes=15
            ),
            AlertRule(
                name="Slow Response Time",
                metric="response_time_ms",
                operator=">",
                threshold=1000.0,
                severity="WARNING",
                cooldown_minutes=5
            ),
            AlertRule(
                name="High Error Rate",
                metric="error_count",
                operator=">",
                threshold=10.0,
                severity="ERROR",
                cooldown_minutes=2
            ),
            AlertRule(
                name="Low Cache Hit Rate",
                metric="cache_hit_rate",
                operator="<",
                threshold=0.7,
                severity="WARNING",
                cooldown_minutes=10
            ),
            AlertRule(
                name="Too Many Active Queries",
                metric="active_queries",
                operator=">",
                threshold=50.0,
                severity="WARNING",
                cooldown_minutes=5
            ),
            AlertRule(
                name="Database Unavailable",
                metric="response_time_ms",
                operator=">",
                threshold=5000.0,
                severity="CRITICAL",
                cooldown_minutes=1
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.name] = rule
    
    def _init_monitoring_database(self):
        """Инициализация БД для мониторинга"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица метрик
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                connection_count INTEGER DEFAULT 0,
                active_queries INTEGER DEFAULT 0,
                slow_queries INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                cache_hit_rate REAL DEFAULT 0.0,
                disk_usage_mb REAL DEFAULT 0.0,
                memory_usage_mb REAL DEFAULT 0.0,
                cpu_usage_percent REAL DEFAULT 0.0,
                response_time_ms REAL DEFAULT 0.0
            )
        ''')
        
        # Таблица алертов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                metric_value REAL NOT NULL,
                threshold REAL NOT NULL,
                details TEXT
            )
        ''')
        
        # Индексы
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
            ON monitoring_metrics(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
            ON monitoring_alerts(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def _collect_system_metrics(self) -> Dict[str, float]:
        """Сбор системных метрик"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Память
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
            
            # Диск
            disk = psutil.disk_usage('/')
            disk_usage_mb = disk.used / 1024 / 1024
            
            return {
                'cpu_usage_percent': cpu_percent,
                'memory_usage_mb': memory_mb,
                'disk_usage_mb': disk_usage_mb
            }
        except Exception as e:
            logger.error(f"Ошибка сбора системных метрик: {e}")
            return {
                'cpu_usage_percent': 0.0,
                'memory_usage_mb': 0.0,
                'disk_usage_mb': 0.0
            }
    
    def _collect_database_metrics(self) -> Dict[str, Any]:
        """Сбор метрик базы данных"""
        try:
            start_time = time.time()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Количество подключений (приблизительно)
            connection_count = 1  # SQLite не поддерживает множественные подключения
            
            # Активные запросы (приблизительно)
            active_queries = 0
            
            # Медленные запросы за последние 5 минут
            cursor.execute('''
                SELECT COUNT(*) FROM query_metrics 
                WHERE timestamp > datetime('now', '-5 minutes') 
                AND execution_time > 1.0
            ''')
            slow_queries = cursor.fetchone()[0]
            
            # Ошибки за последние 5 минут
            cursor.execute('''
                SELECT COUNT(*) FROM security_alerts 
                WHERE timestamp > datetime('now', '-5 minutes') 
                AND severity IN ('ERROR', 'CRITICAL')
            ''')
            error_count = cursor.fetchone()[0]
            
            # Hit rate кэша (приблизительно)
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_expensive = 0 THEN 1 ELSE 0 END) as fast_queries
                FROM query_metrics 
                WHERE timestamp > datetime('now', '-1 hour')
            ''')
            result = cursor.fetchone()
            cache_hit_rate = result[1] / result[0] if result[0] > 0 else 1.0
            
            conn.close()
            
            response_time = (time.time() - start_time) * 1000  # в миллисекундах
            
            return {
                'connection_count': connection_count,
                'active_queries': active_queries,
                'slow_queries': slow_queries,
                'error_count': error_count,
                'cache_hit_rate': cache_hit_rate,
                'response_time_ms': response_time
            }
            
        except Exception as e:
            logger.error(f"Ошибка сбора метрик БД: {e}")
            return {
                'connection_count': 0,
                'active_queries': 0,
                'slow_queries': 0,
                'error_count': 1,  # Считаем ошибку сбора метрик как ошибку
                'cache_hit_rate': 0.0,
                'response_time_ms': 5000.0  # Большое время = проблема
            }
    
    def collect_metrics(self) -> DatabaseMetrics:
        """Сбор всех метрик"""
        system_metrics = self._collect_system_metrics()
        db_metrics = self._collect_database_metrics()
        
        metrics = DatabaseMetrics(
            timestamp=datetime.now(),
            connection_count=db_metrics['connection_count'],
            active_queries=db_metrics['active_queries'],
            slow_queries=db_metrics['slow_queries'],
            error_count=db_metrics['error_count'],
            cache_hit_rate=db_metrics['cache_hit_rate'],
            disk_usage_mb=system_metrics['disk_usage_mb'],
            memory_usage_mb=system_metrics['memory_usage_mb'],
            cpu_usage_percent=system_metrics['cpu_usage_percent'],
            response_time_ms=db_metrics['response_time_ms']
        )
        
        # Сохраняем метрики
        self.metrics_history.append(metrics)
        self._save_metrics_to_db(metrics)
        
        return metrics
    
    def _save_metrics_to_db(self, metrics: DatabaseMetrics):
        """Сохранение метрик в БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO monitoring_metrics 
                (timestamp, connection_count, active_queries, slow_queries, 
                 error_count, cache_hit_rate, disk_usage_mb, memory_usage_mb, 
                 cpu_usage_percent, response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.connection_count,
                metrics.active_queries,
                metrics.slow_queries,
                metrics.error_count,
                metrics.cache_hit_rate,
                metrics.disk_usage_mb,
                metrics.memory_usage_mb,
                metrics.cpu_usage_percent,
                metrics.response_time_ms
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения метрик: {e}")
    
    def _check_alert_rules(self, metrics: DatabaseMetrics):
        """Проверка правил алертинга"""
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # Проверяем cooldown
            if rule.last_triggered:
                time_since_last = datetime.now() - rule.last_triggered
                if time_since_last < timedelta(minutes=rule.cooldown_minutes):
                    continue
            
            # Получаем значение метрики
            metric_value = getattr(metrics, rule.metric, None)
            if metric_value is None:
                continue
            
            # Проверяем условие
            should_alert = False
            if rule.operator == '>':
                should_alert = metric_value > rule.threshold
            elif rule.operator == '<':
                should_alert = metric_value < rule.threshold
            elif rule.operator == '>=':
                should_alert = metric_value >= rule.threshold
            elif rule.operator == '<=':
                should_alert = metric_value <= rule.threshold
            elif rule.operator == '==':
                should_alert = metric_value == rule.threshold
            elif rule.operator == '!=':
                should_alert = metric_value != rule.threshold
            
            if should_alert:
                self._trigger_alert(rule, metric_value, metrics)
    
    def _trigger_alert(self, rule: AlertRule, metric_value: float, metrics: DatabaseMetrics):
        """Срабатывание алерта"""
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            message=f"{rule.name}: {rule.metric} = {metric_value:.2f} {rule.operator} {rule.threshold}",
            timestamp=datetime.now(),
            metric_value=metric_value,
            threshold=rule.threshold,
            details={
                'metric': rule.metric,
                'operator': rule.operator,
                'all_metrics': asdict(metrics)
            }
        )
        
        # Добавляем алерт
        self.alerts.append(alert)
        rule.last_triggered = datetime.now()
        
        # Сохраняем в БД
        self._save_alert_to_db(alert)
        
        # Отправляем уведомления
        self._send_alert_notifications(alert)
        
        # Логируем
        logger.warning(f"ALERT [{rule.severity}]: {alert.message}")
    
    def _save_alert_to_db(self, alert: Alert):
        """Сохранение алерта в БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO monitoring_alerts 
                (rule_name, severity, message, timestamp, metric_value, threshold, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.rule_name,
                alert.severity,
                alert.message,
                alert.timestamp,
                alert.metric_value,
                alert.threshold,
                json.dumps(alert.details) if alert.details else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения алерта: {e}")
    
    def _send_alert_notifications(self, alert: Alert):
        """Отправка уведомлений об алертах"""
        # Email уведомления
        if self.alert_config['email_enabled']:
            self._send_email_alert(alert)
        
        # Webhook уведомления
        if self.alert_config['webhook_enabled']:
            self._send_webhook_alert(alert)
        
        # Slack уведомления
        if self.alert_config['slack_enabled']:
            self._send_slack_alert(alert)
    
    def _send_email_alert(self, alert: Alert):
        """Отправка email алерта"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.alert_config['email_username']
            msg['To'] = ', '.join(self.alert_config['email_recipients'])
            msg['Subject'] = f"[{alert.severity}] Database Alert: {alert.rule_name}"
            
            body = f"""
Database Alert

Rule: {alert.rule_name}
Severity: {alert.severity}
Message: {alert.message}
Timestamp: {alert.timestamp}
Metric Value: {alert.metric_value}
Threshold: {alert.threshold}

Details:
{json.dumps(alert.details, indent=2) if alert.details else 'None'}
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.alert_config['email_smtp_server'], 
                                self.alert_config['email_smtp_port'])
            server.starttls()
            server.login(self.alert_config['email_username'], 
                        self.alert_config['email_password'])
            
            text = msg.as_string()
            server.sendmail(self.alert_config['email_username'], 
                          self.alert_config['email_recipients'], text)
            server.quit()
            
            logger.info(f"Email alert sent: {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки email алерта: {e}")
    
    def _send_webhook_alert(self, alert: Alert):
        """Отправка webhook алерта"""
        try:
            payload = {
                'alert': {
                    'rule_name': alert.rule_name,
                    'severity': alert.severity,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'metric_value': alert.metric_value,
                    'threshold': alert.threshold,
                    'details': alert.details
                }
            }
            
            response = requests.post(
                self.alert_config['webhook_url'],
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook alert sent: {alert.rule_name}")
            else:
                logger.error(f"Webhook alert failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка отправки webhook алерта: {e}")
    
    def _send_slack_alert(self, alert: Alert):
        """Отправка Slack алерта"""
        try:
            # Определяем цвет сообщения по серьезности
            color_map = {
                'INFO': '#36a64f',
                'WARNING': '#ffaa00',
                'ERROR': '#ff0000',
                'CRITICAL': '#8b0000'
            }
            
            color = color_map.get(alert.severity, '#36a64f')
            
            payload = {
                'attachments': [
                    {
                        'color': color,
                        'title': f"Database Alert: {alert.rule_name}",
                        'text': alert.message,
                        'fields': [
                            {
                                'title': 'Severity',
                                'value': alert.severity,
                                'short': True
                            },
                            {
                                'title': 'Metric Value',
                                'value': str(alert.metric_value),
                                'short': True
                            },
                            {
                                'title': 'Threshold',
                                'value': str(alert.threshold),
                                'short': True
                            },
                            {
                                'title': 'Timestamp',
                                'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                'short': True
                            }
                        ],
                        'footer': 'Database Monitoring System',
                        'ts': int(alert.timestamp.timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.alert_config['slack_webhook_url'],
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack alert sent: {alert.rule_name}")
            else:
                logger.error(f"Slack alert failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка отправки Slack алерта: {e}")
    
    def start_monitoring(self, interval_seconds: int = 60):
        """Запуск мониторинга"""
        if self.monitoring_active:
            logger.warning("Мониторинг уже запущен")
            return
        
        self.monitoring_active = True
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    # Собираем метрики
                    metrics = self.collect_metrics()
                    
                    # Проверяем алерты
                    self._check_alert_rules(metrics)
                    
                    logger.debug(f"Метрики собраны: CPU={metrics.cpu_usage_percent:.1f}%, "
                               f"Memory={metrics.memory_usage_mb:.1f}MB, "
                               f"Response={metrics.response_time_ms:.1f}ms")
                    
                except Exception as e:
                    logger.error(f"Ошибка в цикле мониторинга: {e}")
                
                time.sleep(interval_seconds)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"Мониторинг запущен с интервалом {interval_seconds} секунд")
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Мониторинг остановлен")
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Получение сводки метрик за указанный период"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {'message': f'Нет данных за последние {hours} часов'}
        
        # Вычисляем статистики
        cpu_values = [m.cpu_usage_percent for m in recent_metrics]
        memory_values = [m.memory_usage_mb for m in recent_metrics]
        response_values = [m.response_time_ms for m in recent_metrics]
        error_counts = [m.error_count for m in recent_metrics]
        
        return {
            'period_hours': hours,
            'data_points': len(recent_metrics),
            'cpu': {
                'avg': round(sum(cpu_values) / len(cpu_values), 1),
                'max': round(max(cpu_values), 1),
                'min': round(min(cpu_values), 1)
            },
            'memory_mb': {
                'avg': round(sum(memory_values) / len(memory_values), 1),
                'max': round(max(memory_values), 1),
                'min': round(min(memory_values), 1)
            },
            'response_time_ms': {
                'avg': round(sum(response_values) / len(response_values), 1),
                'max': round(max(response_values), 1),
                'min': round(min(response_values), 1)
            },
            'errors': {
                'total': sum(error_counts),
                'max_per_interval': max(error_counts)
            },
            'alerts': {
                'total': len([a for a in self.alerts if a.timestamp > cutoff_time]),
                'critical': len([a for a in self.alerts if a.severity == 'CRITICAL' and a.timestamp > cutoff_time]),
                'error': len([a for a in self.alerts if a.severity == 'ERROR' and a.timestamp > cutoff_time]),
                'warning': len([a for a in self.alerts if a.severity == 'WARNING' and a.timestamp > cutoff_time])
            }
        }
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получение последних алертов"""
        recent_alerts = list(self.alerts)[-limit:]
        
        return [
            {
                'rule_name': alert.rule_name,
                'severity': alert.severity,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'metric_value': alert.metric_value,
                'threshold': alert.threshold
            }
            for alert in recent_alerts
        ]
    
    def add_alert_rule(self, rule: AlertRule):
        """Добавление правила алертинга"""
        self.alert_rules[rule.name] = rule
        logger.info(f"Добавлено правило алертинга: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """Удаление правила алертинга"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"Удалено правило алертинга: {rule_name}")
    
    def update_alert_config(self, config: Dict[str, Any]):
        """Обновление конфигурации алертинга"""
        self.alert_config.update(config)
        logger.info(f"Конфигурация алертинга обновлена: {config}")

# Глобальный экземпляр мониторинга
_global_monitor = None

def get_monitor() -> DatabaseMonitoringSystem:
    """Получение глобального экземпляра мониторинга"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = DatabaseMonitoringSystem()
    return _global_monitor

# Пример использования
if __name__ == "__main__":
    # Создаем систему мониторинга
    monitor = DatabaseMonitoringSystem()
    
    # Настраиваем алертинг
    monitor.update_alert_config({
        'email_enabled': False,  # Включить для реального использования
        'slack_enabled': False,  # Включить для реального использования
        'webhook_enabled': False  # Включить для реального использования
    })
    
    # Запускаем мониторинг
    monitor.start_monitoring(interval_seconds=10)
    
    try:
        # Ждем некоторое время для сбора метрик
        time.sleep(30)
        
        # Получаем сводку
        summary = monitor.get_metrics_summary(hours=1)
        print(f"Сводка метрик: {summary}")
        
        # Получаем алерты
        alerts = monitor.get_recent_alerts()
        print(f"Последние алерты: {len(alerts)}")
        
    finally:
        # Останавливаем мониторинг
        monitor.stop_monitoring()