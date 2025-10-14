"""
Монитор токенов для автоматической оптимизации и предотвращения проблем
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class TokenUsageStats:
    """Статистика использования токенов"""
    total_tokens: int = 0
    total_requests: int = 0
    truncated_responses: int = 0
    avg_response_length: float = 0.0
    avg_tokens_per_request: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class UserPatterns:
    """Паттерны использования пользователя"""
    user_id: int
    preferred_prompt_length: str = "medium"
    preferred_style: str = "balanced"
    avg_conversation_length: int = 0
    avg_response_length: float = 0.0
    truncation_rate: float = 0.0
    satisfaction_score: float = 0.0
    last_optimization: datetime = field(default_factory=datetime.now)

@dataclass
class OptimizationSuggestion:
    """Предложение по оптимизации"""
    type: str  # 'prompt_length', 'context_compression', 'response_splitting'
    priority: int  # 1-5, где 5 - высший приоритет
    description: str
    expected_improvement: str
    auto_apply: bool = False

class TokenMonitor:
    """Монитор токенов с автоматической оптимизацией"""
    
    def __init__(self, config):
        self.config = config
        self.usage_stats = TokenUsageStats()
        self.user_patterns = {}  # user_id -> UserPatterns
        self.optimization_history = deque(maxlen=1000)
        self.alert_thresholds = {
            'high_token_usage': 0.8,  # 80% от лимита
            'high_truncation_rate': 0.3,  # 30% обрезанных ответов
            'low_satisfaction': 3.0  # Оценка ниже 3.0
        }
        
        # Кэш для быстрого доступа
        self._response_cache = {}
        self._pattern_cache = {}
        
    def track_request(
        self, 
        user_id: int, 
        prompt_tokens: int, 
        response_tokens: int,
        response_length: int,
        truncated: bool = False,
        satisfaction: Optional[float] = None
    ):
        """Отслеживание запроса пользователя"""
        
        # Обновляем общую статистику
        self.usage_stats.total_tokens += prompt_tokens + response_tokens
        self.usage_stats.total_requests += 1
        self.usage_stats.avg_tokens_per_request = (
            self.usage_stats.total_tokens / self.usage_stats.total_requests
        )
        
        if truncated:
            self.usage_stats.truncated_responses += 1
        
        # Обновляем статистику пользователя
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = UserPatterns(user_id=user_id)
        
        user_patterns = self.user_patterns[user_id]
        
        # Обновляем среднюю длину ответа
        if user_patterns.avg_response_length == 0:
            user_patterns.avg_response_length = response_length
        else:
            user_patterns.avg_response_length = (
                (user_patterns.avg_response_length * 0.8) + (response_length * 0.2)
            )
        
        # Обновляем статистику обрезания
        if truncated:
            user_patterns.truncation_rate = min(
                user_patterns.truncation_rate + 0.1, 1.0
            )
        else:
            user_patterns.truncation_rate = max(
                user_patterns.truncation_rate - 0.05, 0.0
            )
        
        # Обновляем оценку удовлетворенности
        if satisfaction is not None:
            if user_patterns.satisfaction_score == 0:
                user_patterns.satisfaction_score = satisfaction
            else:
                user_patterns.satisfaction_score = (
                    (user_patterns.satisfaction_score * 0.7) + (satisfaction * 0.3)
                )
        
        # Проверяем необходимость оптимизации
        self._check_optimization_needed(user_id)
        
        logger.debug(f"Отслежен запрос пользователя {user_id}: {prompt_tokens + response_tokens} токенов")
    
    def predict_token_overflow(
        self, 
        conversation_history: List[str], 
        new_message: str,
        user_id: int
    ) -> Tuple[bool, int]:
        """Предсказание переполнения токенов"""
        
        # Получаем паттерны пользователя
        user_patterns = self.user_patterns.get(user_id, UserPatterns(user_id=user_id))
        
        # Оцениваем токены в новом сообщении
        new_message_tokens = len(new_message) // 4  # Примерная оценка
        
        # Оцениваем токены в истории
        history_tokens = sum(len(msg) // 4 for msg in conversation_history)
        
        # Получаем лимиты для пользователя
        user_limits = self.config.get_user_limits("free")  # Пока только free
        max_tokens = user_limits["max_tokens"]
        
        # Резервируем место для ответа
        available_tokens = max_tokens - self.config.RESPONSE_TOKENS
        
        total_estimated = history_tokens + new_message_tokens
        
        overflow = total_estimated > available_tokens
        overflow_percentage = total_estimated / available_tokens if available_tokens > 0 else 1.0
        
        return overflow, int(overflow_percentage * 100)
    
    def get_optimal_token_limit(self, user_id: int, context_length: int) -> int:
        """Получение оптимального лимита токенов для пользователя"""
        
        user_patterns = self.user_patterns.get(user_id, UserPatterns(user_id=user_id))
        base_limits = self.config.get_user_limits("free")
        base_limit = base_limits["max_tokens"]
        
        # Адаптация на основе паттернов пользователя
        if user_patterns.truncation_rate > 0.3:
            # Если часто обрезаются ответы, уменьшаем лимит
            optimal_limit = int(base_limit * 0.7)
        elif user_patterns.avg_response_length > 500:
            # Если пользователь любит длинные ответы, увеличиваем
            optimal_limit = int(base_limit * 1.2)
        else:
            optimal_limit = base_limit
        
        # Адаптация на основе длины контекста
        if context_length > 15:
            optimal_limit = max(optimal_limit - 500, self.config.MIN_TOKENS)
        elif context_length < 5:
            optimal_limit = min(optimal_limit + 300, self.config.MAX_TOKENS + 500)
        
        return optimal_limit
    
    def get_optimization_suggestions(self, user_id: int) -> List[OptimizationSuggestion]:
        """Получение предложений по оптимизации для пользователя"""
        
        suggestions = []
        user_patterns = self.user_patterns.get(user_id, UserPatterns(user_id=user_id))
        
        # Предложения на основе статистики обрезания
        if user_patterns.truncation_rate > 0.2:
            suggestions.append(OptimizationSuggestion(
                type="prompt_length",
                priority=4,
                description="Часто обрезаются ответы",
                expected_improvement="Уменьшить длину промптов на 20%",
                auto_apply=True
            ))
        
        # Предложения на основе длины ответов
        if user_patterns.avg_response_length < 200:
            suggestions.append(OptimizationSuggestion(
                type="response_expansion",
                priority=3,
                description="Ответы слишком короткие",
                expected_improvement="Увеличить детализацию ответов",
                auto_apply=False
            ))
        
        # Предложения на основе удовлетворенности
        if user_patterns.satisfaction_score > 0 and user_patterns.satisfaction_score < 3.0:
            suggestions.append(OptimizationSuggestion(
                type="style_adaptation",
                priority=5,
                description="Низкая удовлетворенность пользователя",
                expected_improvement="Адаптировать стиль под предпочтения",
                auto_apply=True
            ))
        
        # Предложения на основе общей статистики
        if self.usage_stats.truncated_responses / max(self.usage_stats.total_requests, 1) > 0.15:
            suggestions.append(OptimizationSuggestion(
                type="global_optimization",
                priority=3,
                description="Высокий процент обрезанных ответов в системе",
                expected_improvement="Глобальная оптимизация лимитов токенов",
                auto_apply=True
            ))
        
        return suggestions
    
    def auto_optimize_user(self, user_id: int) -> Dict[str, Any]:
        """Автоматическая оптимизация для пользователя"""
        
        user_patterns = self.user_patterns.get(user_id, UserPatterns(user_id=user_id))
        suggestions = self.get_optimization_suggestions(user_id)
        
        applied_optimizations = []
        
        for suggestion in suggestions:
            if suggestion.auto_apply:
                optimization_result = self._apply_optimization(user_id, suggestion)
                if optimization_result['success']:
                    applied_optimizations.append(optimization_result)
        
        # Обновляем время последней оптимизации
        user_patterns.last_optimization = datetime.now()
        
        # Записываем в историю
        self.optimization_history.append({
            'user_id': user_id,
            'timestamp': datetime.now(),
            'applied_optimizations': applied_optimizations,
            'user_patterns': user_patterns
        })
        
        return {
            'user_id': user_id,
            'applied_optimizations': applied_optimizations,
            'remaining_suggestions': [s for s in suggestions if not s.auto_apply]
        }
    
    def _apply_optimization(self, user_id: int, suggestion: OptimizationSuggestion) -> Dict[str, Any]:
        """Применение оптимизации"""
        
        user_patterns = self.user_patterns.get(user_id, UserPatterns(user_id=user_id))
        
        try:
            if suggestion.type == "prompt_length":
                # Уменьшаем предпочитаемую длину промпта
                if user_patterns.preferred_prompt_length == "long":
                    user_patterns.preferred_prompt_length = "medium"
                elif user_patterns.preferred_prompt_length == "medium":
                    user_patterns.preferred_prompt_length = "short"
                
                return {
                    'success': True,
                    'type': 'prompt_length',
                    'description': f"Изменена предпочитаемая длина промпта на {user_patterns.preferred_prompt_length}"
                }
            
            elif suggestion.type == "style_adaptation":
                # Адаптируем стиль
                if user_patterns.satisfaction_score < 3.0:
                    user_patterns.preferred_style = "detailed"
                else:
                    user_patterns.preferred_style = "concise"
                
                return {
                    'success': True,
                    'type': 'style_adaptation',
                    'description': f"Изменен стиль на {user_patterns.preferred_style}"
                }
            
            else:
                return {
                    'success': False,
                    'type': suggestion.type,
                    'description': f"Автоматическое применение не поддерживается для {suggestion.type}"
                }
        
        except Exception as e:
            logger.error(f"Ошибка применения оптимизации {suggestion.type} для пользователя {user_id}: {e}")
            return {
                'success': False,
                'type': suggestion.type,
                'description': f"Ошибка: {str(e)}"
            }
    
    def _check_optimization_needed(self, user_id: int):
        """Проверка необходимости оптимизации"""
        
        user_patterns = self.user_patterns.get(user_id, UserPatterns(user_id=user_id))
        
        # Проверяем, прошло ли достаточно времени с последней оптимизации
        time_since_last = datetime.now() - user_patterns.last_optimization
        if time_since_last < timedelta(minutes=30):
            return
        
        # Проверяем критерии для оптимизации
        needs_optimization = (
            user_patterns.truncation_rate > 0.2 or
            (user_patterns.satisfaction_score > 0 and user_patterns.satisfaction_score < 3.0) or
            user_patterns.avg_response_length < 100
        )
        
        if needs_optimization:
            logger.info(f"Пользователь {user_id} нуждается в оптимизации")
            self.auto_optimize_user(user_id)
    
    def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """Получение инсайтов о пользователе"""
        
        user_patterns = self.user_patterns.get(user_id, UserPatterns(user_id=user_id))
        
        return {
            'user_id': user_id,
            'patterns': {
                'preferred_prompt_length': user_patterns.preferred_prompt_length,
                'preferred_style': user_patterns.preferred_style,
                'avg_conversation_length': user_patterns.avg_conversation_length,
                'truncation_rate': user_patterns.truncation_rate,
                'satisfaction_score': user_patterns.satisfaction_score
            },
            'optimization_status': {
                'last_optimization': user_patterns.last_optimization.isoformat(),
                'needs_optimization': self._needs_optimization(user_patterns)
            },
            'recommendations': self.get_optimization_suggestions(user_id)
        }
    
    def _needs_optimization(self, user_patterns: UserPatterns) -> bool:
        """Проверка, нужна ли оптимизация"""
        return (
            user_patterns.truncation_rate > 0.2 or
            (user_patterns.satisfaction_score > 0 and user_patterns.satisfaction_score < 3.0) or
            user_patterns.avg_response_length < 100
        )
    
    def get_system_health(self) -> Dict[str, Any]:
        """Получение состояния системы"""
        
        total_requests = self.usage_stats.total_requests
        truncation_rate = (
            self.usage_stats.truncated_responses / total_requests 
            if total_requests > 0 else 0
        )
        
        return {
            'total_requests': total_requests,
            'total_tokens': self.usage_stats.total_tokens,
            'avg_tokens_per_request': self.usage_stats.avg_tokens_per_request,
            'truncation_rate': truncation_rate,
            'active_users': len(self.user_patterns),
            'optimization_alerts': self._get_system_alerts()
        }
    
    def _get_system_alerts(self) -> List[str]:
        """Получение системных предупреждений"""
        
        alerts = []
        total_requests = self.usage_stats.total_requests
        
        if total_requests > 0:
            truncation_rate = self.usage_stats.truncated_responses / total_requests
            
            if truncation_rate > self.alert_thresholds['high_truncation_rate']:
                alerts.append(f"Высокий процент обрезанных ответов: {truncation_rate:.1%}")
            
            if self.usage_stats.avg_tokens_per_request > self.config.MAX_TOKENS * 0.8:
                alerts.append("Высокое среднее потребление токенов")
        
        return alerts
    
    def reset_user_stats(self, user_id: int):
        """Сброс статистики пользователя"""
        
        if user_id in self.user_patterns:
            del self.user_patterns[user_id]
            logger.info(f"Статистика пользователя {user_id} сброшена")
    
    def export_stats(self) -> Dict[str, Any]:
        """Экспорт статистики для анализа"""
        
        return {
            'usage_stats': {
                'total_tokens': self.usage_stats.total_tokens,
                'total_requests': self.usage_stats.total_requests,
                'truncated_responses': self.usage_stats.truncated_responses,
                'avg_response_length': self.usage_stats.avg_response_length,
                'avg_tokens_per_request': self.usage_stats.avg_tokens_per_request,
                'last_updated': self.usage_stats.last_updated.isoformat()
            },
            'user_patterns': {
                user_id: {
                    'preferred_prompt_length': patterns.preferred_prompt_length,
                    'preferred_style': patterns.preferred_style,
                    'avg_conversation_length': patterns.avg_conversation_length,
                    'truncation_rate': patterns.truncation_rate,
                    'satisfaction_score': patterns.satisfaction_score,
                    'last_optimization': patterns.last_optimization.isoformat()
                }
                for user_id, patterns in self.user_patterns.items()
            },
            'optimization_history': [
                {
                    'user_id': opt['user_id'],
                    'timestamp': opt['timestamp'].isoformat(),
                    'applied_optimizations': opt['applied_optimizations']
                }
                for opt in self.optimization_history
            ]
        }