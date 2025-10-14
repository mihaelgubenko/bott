"""
Клиент OpenAI с интегрированным управлением токенами и кэшированием
"""

import openai
import time
import logging
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass

from .token_manager import TokenManager, TokenUsage
from .response_cache import ResponseCache
from .token_monitor import TokenMonitor
from .adaptive_prompt_manager import AdaptivePromptManager, PromptType

logger = logging.getLogger(__name__)

@dataclass
class AIResponse:
    """Ответ от ИИ с метаданными"""
    content: str
    usage: TokenUsage
    cached: bool = False
    truncated: bool = False
    response_time: float = 0.0
    model: str = "gpt-4"

class OpenAIClient:
    """Клиент OpenAI с интегрированными оптимизациями"""
    
    def __init__(self, config):
        self.config = config
        self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Инициализируем компоненты
        self.token_manager = TokenManager(config)
        self.response_cache = ResponseCache(config)
        self.token_monitor = TokenMonitor(config)
        self.prompt_manager = AdaptivePromptManager(config)
        
        # Настройки модели
        self.model_settings = {
            "gpt-4": {
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 60
            },
            "gpt-3.5-turbo": {
                "max_tokens": 2000,
                "temperature": 0.7,
                "timeout": 30
            }
        }
    
    async def get_response(
        self,
        prompt: str,
        user_id: int,
        prompt_type: PromptType = PromptType.PSYCHOLOGY_CONSULTATION,
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        force_fresh: bool = False
    ) -> AIResponse:
        """Получение ответа от ИИ с оптимизацией"""
        
        start_time = time.time()
        context = context or {}
        
        # Проверяем кэш
        if use_cache and not force_fresh:
            cached_response = self.response_cache.get(
                prompt, user_id, 
                context.get('conversation', ''), 
                prompt_type.value
            )
            if cached_response:
                logger.debug(f"Использован кэшированный ответ для пользователя {user_id}")
                return AIResponse(
                    content=cached_response,
                    usage=TokenUsage(0, 0, 0, 0.0),
                    cached=True,
                    response_time=0.0
                )
        
        # Получаем оптимальный промпт
        available_tokens = self._calculate_available_tokens(user_id, context)
        optimal_prompt, prompt_variant_id = self.prompt_manager.get_optimal_prompt(
            prompt_type, available_tokens, user_id, context
        )
        
        # Оптимизируем промпт с учетом токенов
        optimized_prompt, optimized_context, token_usage = self.token_manager.optimize_prompt(
            optimal_prompt, context.get('conversation', ''), "free"
        )
        
        # Получаем ответ от OpenAI
        try:
            response = await self._call_openai(optimized_prompt, optimized_context, user_id)
            
            # Проверяем, не обрезан ли ответ
            is_truncated = self.token_manager.is_response_truncated(response)
            
            # Если ответ обрезан, пытаемся продолжить
            if is_truncated:
                continuation = await self._continue_response(response, user_id)
                response = response + "\n\n" + continuation
                logger.info(f"Продолжен обрезанный ответ для пользователя {user_id}")
            
            # Разбиваем длинный ответ на части
            response_parts = self.token_manager.split_long_response(response)
            final_response = response_parts[0] if response_parts else response
            
            # Обновляем статистику
            response_time = time.time() - start_time
            self.token_monitor.track_request(
                user_id=user_id,
                prompt_tokens=token_usage.prompt_tokens,
                response_tokens=len(final_response) // 4,  # Примерная оценка
                response_length=len(final_response),
                truncated=is_truncated
            )
            
            # Сохраняем в кэш
            if use_cache and not is_truncated:
                self.response_cache.put(
                    prompt=prompt,
                    response=final_response,
                    user_id=user_id,
                    context=context.get('conversation', ''),
                    response_type=prompt_type.value,
                    metadata={
                        'prompt_variant': prompt_variant_id,
                        'user_id': user_id,
                        'response_time': response_time,
                        'truncated': is_truncated
                    }
                )
            
            return AIResponse(
                content=final_response,
                usage=token_usage,
                cached=False,
                truncated=is_truncated,
                response_time=response_time,
                model="gpt-4"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении ответа от OpenAI: {e}")
            return AIResponse(
                content="Извините, произошла ошибка при обработке запроса. Попробуйте позже.",
                usage=TokenUsage(0, 0, 0, 0.0),
                cached=False,
                truncated=False,
                response_time=time.time() - start_time
            )
    
    async def _call_openai(self, prompt: str, context: str, user_id: int) -> str:
        """Вызов OpenAI API"""
        
        # Формируем полный промпт
        full_prompt = f"{prompt}\n\n{context}" if context else prompt
        
        # Получаем настройки модели
        model_settings = self.model_settings["gpt-4"]
        
        # Получаем оптимальный лимит токенов для пользователя
        optimal_limit = self.token_monitor.get_optimal_token_limit(user_id, len(context.split('\n')))
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=min(optimal_limit, model_settings["max_tokens"]),
                temperature=model_settings["temperature"],
                timeout=model_settings["timeout"]
            )
            
            return response.choices[0].message.content.strip()
            
        except openai.RateLimitError:
            logger.warning(f"Превышен лимит запросов для пользователя {user_id}")
            return "Извините, слишком много запросов. Попробуйте через несколько минут."
        
        except openai.APITimeoutError:
            logger.warning(f"Таймаут API для пользователя {user_id}")
            return "Извините, запрос занял слишком много времени. Попробуйте еще раз."
        
        except Exception as e:
            logger.error(f"Неожиданная ошибка OpenAI: {e}")
            raise
    
    async def _continue_response(self, truncated_response: str, user_id: int) -> str:
        """Продолжение обрезанного ответа"""
        
        continuation_prompt = self.token_manager.get_continuation_prompt(truncated_response)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": continuation_prompt}],
                max_tokens=500,  # Ограничиваем продолжение
                temperature=0.7,
                timeout=30
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при продолжении ответа: {e}")
            return ""
    
    def _calculate_available_tokens(self, user_id: int, context: Dict[str, Any]) -> int:
        """Расчет доступных токенов для пользователя"""
        
        # Базовый лимит
        base_limits = self.config.get_user_limits("free")
        base_limit = base_limits["max_tokens"]
        
        # Адаптивные лимиты на основе контекста
        conversation_length = len(context.get('conversation', '').split('\n'))
        adaptive_limits = self.config.get_adaptive_limits(conversation_length, "free")
        
        # Получаем оптимальный лимит от монитора
        optimal_limit = self.token_monitor.get_optimal_token_limit(user_id, conversation_length)
        
        # Возвращаем минимальный из всех лимитов
        return min(base_limit, adaptive_limits["max_tokens"], optimal_limit)
    
    def get_user_optimization_status(self, user_id: int) -> Dict[str, Any]:
        """Получение статуса оптимизации для пользователя"""
        
        return {
            'user_insights': self.token_monitor.get_user_insights(user_id),
            'cache_stats': self.response_cache.get_cache_stats(),
            'optimization_suggestions': self.token_monitor.get_optimization_suggestions(user_id)
        }
    
    def optimize_user_experience(self, user_id: int) -> Dict[str, Any]:
        """Оптимизация пользовательского опыта"""
        
        # Автоматическая оптимизация через монитор
        optimization_result = self.token_monitor.auto_optimize_user(user_id)
        
        # Очистка кэша пользователя при необходимости
        user_patterns = self.token_monitor.user_patterns.get(user_id)
        if user_patterns and user_patterns.truncation_rate > 0.5:
            self.response_cache.invalidate_user(user_id)
            optimization_result['cache_cleared'] = True
        
        return optimization_result
    
    def get_system_health(self) -> Dict[str, Any]:
        """Получение состояния системы"""
        
        return {
            'token_monitor': self.token_monitor.get_system_health(),
            'response_cache': self.response_cache.get_cache_stats(),
            'prompt_manager': self.prompt_manager.get_template_stats()
        }
    
    def clear_user_data(self, user_id: int):
        """Очистка данных пользователя"""
        
        # Очищаем кэш
        self.response_cache.invalidate_user(user_id)
        
        # Сбрасываем статистику
        self.token_monitor.reset_user_stats(user_id)
        
        logger.info(f"Данные пользователя {user_id} очищены")
    
    def export_analytics(self) -> Dict[str, Any]:
        """Экспорт аналитики"""
        
        return {
            'token_monitor': self.token_monitor.export_stats(),
            'response_cache': self.response_cache.export_cache(),
            'system_health': self.get_system_health()
        }