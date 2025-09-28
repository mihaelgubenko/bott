"""
Система оптимизации модели и параметров для максимальной точности
"""
import openai
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Типы моделей для разных задач"""
    PSYCHOLOGY_CONSULTATION = "psychology"
    CAREER_ANALYSIS = "career"
    EXPRESS_ANALYSIS = "express"
    FULL_ANALYSIS = "full"

@dataclass
class ModelConfig:
    """Конфигурация модели"""
    model_name: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    timeout: int
    retry_count: int

@dataclass
class OptimizationResult:
    """Результат оптимизации"""
    config: ModelConfig
    performance_score: float
    response_time: float
    quality_metrics: Dict[str, float]
    timestamp: datetime

class ModelOptimizer:
    """Оптимизатор модели для максимальной точности"""
    
    def __init__(self, db_path: str = 'optimization.db'):
        self.db_path = db_path
        self.init_database()
        self._load_optimal_configs()
    
    def init_database(self):
        """Инициализация базы данных для оптимизации"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_type TEXT NOT NULL,
                model_name TEXT NOT NULL,
                temperature REAL NOT NULL,
                max_tokens INTEGER NOT NULL,
                top_p REAL NOT NULL,
                frequency_penalty REAL NOT NULL,
                presence_penalty REAL NOT NULL,
                timeout INTEGER NOT NULL,
                retry_count INTEGER NOT NULL,
                performance_score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_type TEXT NOT NULL,
                config_id INTEGER NOT NULL,
                performance_score REAL NOT NULL,
                response_time REAL NOT NULL,
                quality_metrics TEXT NOT NULL,
                test_prompt TEXT NOT NULL,
                test_response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (config_id) REFERENCES model_configs (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_optimal_configs(self):
        """Загружает оптимальные конфигурации для разных типов задач"""
        self.optimal_configs = {
            ModelType.PSYCHOLOGY_CONSULTATION: ModelConfig(
                model_name="gpt-4",
                temperature=0.7,  # Баланс между креативностью и точностью
                max_tokens=400,
                top_p=0.9,
                frequency_penalty=0.1,  # Небольшое разнообразие
                presence_penalty=0.0,
                timeout=30,
                retry_count=2
            ),
            ModelType.CAREER_ANALYSIS: ModelConfig(
                model_name="gpt-4",
                temperature=0.6,  # Более структурированные ответы
                max_tokens=500,
                top_p=0.85,
                frequency_penalty=0.2,
                presence_penalty=0.1,
                timeout=45,
                retry_count=2
            ),
            ModelType.EXPRESS_ANALYSIS: ModelConfig(
                model_name="gpt-4",
                temperature=0.5,  # Максимальная точность
                max_tokens=600,
                top_p=0.8,
                frequency_penalty=0.3,
                presence_penalty=0.2,
                timeout=60,
                retry_count=3
            ),
            ModelType.FULL_ANALYSIS: ModelConfig(
                model_name="gpt-4",
                temperature=0.4,  # Очень точные и детальные ответы
                max_tokens=2000,
                top_p=0.75,
                frequency_penalty=0.4,
                presence_penalty=0.3,
                timeout=90,
                retry_count=3
            )
        }
    
    def get_optimized_config(self, model_type: ModelType, 
                           user_context: Dict = None) -> ModelConfig:
        """Получает оптимизированную конфигурацию для типа задачи"""
        base_config = self.optimal_configs[model_type]
        
        # Адаптируем конфигурацию на основе контекста пользователя
        if user_context:
            config = self._adapt_config_to_context(base_config, user_context)
        else:
            config = base_config
        
        # Проверяем, есть ли более оптимальная конфигурация в базе
        optimized_config = self._get_best_config_from_db(model_type)
        if optimized_config and optimized_config.performance_score > 0.8:
            return optimized_config
        
        return config
    
    def _adapt_config_to_context(self, base_config: ModelConfig, 
                                user_context: Dict) -> ModelConfig:
        """Адаптирует конфигурацию под контекст пользователя"""
        config = ModelConfig(
            model_name=base_config.model_name,
            temperature=base_config.temperature,
            max_tokens=base_config.max_tokens,
            top_p=base_config.top_p,
            frequency_penalty=base_config.frequency_penalty,
            presence_penalty=base_config.presence_penalty,
            timeout=base_config.timeout,
            retry_count=base_config.retry_count
        )
        
        # Адаптация на основе опыта пользователя
        user_interactions = user_context.get('total_interactions', 0)
        if user_interactions > 50:
            # Опытные пользователи - более сложные ответы
            config.max_tokens = min(2000, config.max_tokens + 200)
            config.temperature = min(0.8, config.temperature + 0.1)
        elif user_interactions < 5:
            # Новые пользователи - более простые ответы
            config.max_tokens = max(200, config.max_tokens - 100)
            config.temperature = max(0.3, config.temperature - 0.1)
        
        # Адаптация на основе сложности вопроса
        question_complexity = user_context.get('question_complexity', 0.5)
        if question_complexity > 0.8:
            config.max_tokens = min(2000, config.max_tokens + 300)
            config.timeout = min(120, config.timeout + 30)
        elif question_complexity < 0.3:
            config.max_tokens = max(150, config.max_tokens - 150)
        
        return config
    
    def _get_best_config_from_db(self, model_type: ModelType) -> Optional[ModelConfig]:
        """Получает лучшую конфигурацию из базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT model_name, temperature, max_tokens, top_p, 
                   frequency_penalty, presence_penalty, timeout, retry_count
            FROM model_configs 
            WHERE model_type = ? AND performance_score > 0.8
            ORDER BY performance_score DESC
            LIMIT 1
        ''', (model_type.value,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return ModelConfig(
            model_name=result[0],
            temperature=result[1],
            max_tokens=result[2],
            top_p=result[3],
            frequency_penalty=result[4],
            presence_penalty=result[5],
            timeout=result[6],
            retry_count=result[7]
        )
    
    async def generate_optimized_response(self, prompt: str, model_type: ModelType,
                                        user_context: Dict = None,
                                        api_key: str = None) -> Tuple[str, Dict[str, Any]]:
        """Генерирует оптимизированный ответ с лучшими параметрами"""
        if api_key is None:
            raise ValueError("API key is required")
        
        config = self.get_optimized_config(model_type, user_context)
        client = openai.OpenAI(api_key=api_key)
        
        start_time = datetime.now()
        
        try:
            response = client.chat.completions.create(
                model=config.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                timeout=config.timeout,
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            response_text = response.choices[0].message.content.strip()
            
            # Собираем метрики производительности
            performance_metrics = {
                'response_time': response_time,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'model_used': config.model_name,
                'config_applied': {
                    'temperature': config.temperature,
                    'max_tokens': config.max_tokens,
                    'top_p': config.top_p
                }
            }
            
            return response_text, performance_metrics
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def save_optimization_result(self, model_type: ModelType, config: ModelConfig,
                               performance_score: float, response_time: float,
                               quality_metrics: Dict[str, float], test_prompt: str,
                               test_response: str):
        """Сохраняет результат оптимизации"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Сохраняем конфигурацию
        cursor.execute('''
            INSERT INTO model_configs 
            (model_type, model_name, temperature, max_tokens, top_p, 
             frequency_penalty, presence_penalty, timeout, retry_count, performance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_type.value, config.model_name, config.temperature,
            config.max_tokens, config.top_p, config.frequency_penalty,
            config.presence_penalty, config.timeout, config.retry_count,
            performance_score
        ))
        
        config_id = cursor.lastrowid
        
        # Сохраняем результат оптимизации
        cursor.execute('''
            INSERT INTO optimization_results 
            (model_type, config_id, performance_score, response_time, 
             quality_metrics, test_prompt, test_response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_type.value, config_id, performance_score, response_time,
            json.dumps(quality_metrics), test_prompt, test_response
        ))
        
        conn.commit()
        conn.close()
    
    def run_optimization_experiment(self, model_type: ModelType, test_prompts: List[str],
                                  api_key: str) -> List[OptimizationResult]:
        """Запускает эксперимент оптимизации с разными конфигурациями"""
        results = []
        
        # Тестируем разные температуры
        temperatures = [0.3, 0.5, 0.7, 0.9]
        
        for temp in temperatures:
            config = self.optimal_configs[model_type]
            config.temperature = temp
            
            total_score = 0
            total_time = 0
            quality_metrics = {}
            
            for prompt in test_prompts:
                try:
                    response_text, metrics = await self.generate_optimized_response(
                        prompt, model_type, api_key=api_key
                    )
                    
                    # Оцениваем качество ответа (упрощенная версия)
                    quality_score = self._evaluate_response_quality(prompt, response_text)
                    total_score += quality_score
                    total_time += metrics['response_time']
                    
                except Exception as e:
                    logger.error(f"Error in optimization experiment: {e}")
                    continue
            
            avg_score = total_score / len(test_prompts) if test_prompts else 0
            avg_time = total_time / len(test_prompts) if test_prompts else 0
            
            result = OptimizationResult(
                config=config,
                performance_score=avg_score,
                response_time=avg_time,
                quality_metrics=quality_metrics,
                timestamp=datetime.now()
            )
            
            results.append(result)
            
            # Сохраняем результат
            self.save_optimization_result(
                model_type, config, avg_score, avg_time, 
                quality_metrics, str(test_prompts), "test_response"
            )
        
        return results
    
    def _evaluate_response_quality(self, prompt: str, response: str) -> float:
        """Упрощенная оценка качества ответа"""
        score = 0.5
        
        # Длина ответа
        if len(response) > 100:
            score += 0.1
        if len(response) > 300:
            score += 0.1
        
        # Наличие ключевых слов
        quality_keywords = ['понимаю', 'рекомендую', 'анализ', 'профиль', 'характер']
        keyword_count = sum(1 for keyword in quality_keywords if keyword in response.lower())
        score += min(0.2, keyword_count * 0.05)
        
        # Структурированность (наличие эмодзи или списков)
        if '🎯' in response or '📊' in response or '•' in response:
            score += 0.1
        
        return min(1.0, score)
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Получает статистику оптимизации"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT model_type, AVG(performance_score), COUNT(*), 
                   AVG(response_time), MAX(performance_score)
            FROM optimization_results 
            GROUP BY model_type
        ''')
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {
                'average_score': row[1] or 0.0,
                'total_experiments': row[2],
                'average_response_time': row[3] or 0.0,
                'best_score': row[4] or 0.0
            }
        
        conn.close()
        return stats

# Глобальный экземпляр оптимизатора
model_optimizer = ModelOptimizer()