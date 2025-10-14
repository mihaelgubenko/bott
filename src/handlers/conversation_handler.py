"""
Обработчик диалогов с интегрированным управлением токенами
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..ai.adaptive_prompt_manager import PromptType

logger = logging.getLogger(__name__)

class ConversationHandler:
    """Обработчик диалогов с умным управлением контекстом"""
    
    def __init__(self, ai_client, database):
        self.ai_client = ai_client
        self.database = database
        self.conversation_history = {}  # user_id -> list of messages
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка входящих сообщений"""
        user = update.effective_user
        text = update.message.text.strip()
        
        if not text:
            await update.message.reply_text("Пожалуйста, напишите что-то конкретное.")
            return 'WAITING_MESSAGE'
        
        # Инициализируем историю пользователя
        if user.id not in self.conversation_history:
            self.conversation_history[user.id] = []
        
        # Добавляем сообщение в историю
        self.conversation_history[user.id].append(text)
        
        # Ограничиваем длину истории
        if len(self.conversation_history[user.id]) > 20:
            self.conversation_history[user.id] = self.conversation_history[user.id][-20:]
        
        # Анализируем паттерны речи
        patterns = self._analyze_speech_patterns(text)
        
        # Обрабатываем специальные случаи
        if patterns['cancellation']:
            return await self._handle_cancellation(update, context)
        
        if patterns['topic_change']:
            return await self._handle_topic_change(update, context)
        
        if patterns['self_introduction_request']:
            return await self._handle_self_introduction(update, context)
        
        # ПРИОРИТЕТ: Если пользователь задает прямой вопрос - отвечаем сразу
        if self._is_direct_question(text):
            response_type = self._determine_response_type(patterns, text)
            try:
                response = await self._get_ai_response(user.id, text, response_type)
                await self._send_response(update, response)
                return 'WAITING_MESSAGE'
            except Exception as e:
                logger.error(f"Ошибка получения ответа ИИ: {e}")
                await update.message.reply_text(
                    "Извините, произошла ошибка при обработке запроса. Попробуйте позже."
                )
                return 'WAITING_MESSAGE'
        
        # Определяем тип ответа
        response_type = self._determine_response_type(patterns, text)
        
        # Получаем ответ от ИИ
        try:
            response = await self._get_ai_response(user.id, text, response_type)
            
            # Отправляем ответ
            await self._send_response(update, response)
            
            # Предлагаем дополнительные опции
            await self._suggest_next_steps(update, patterns, len(self.conversation_history[user.id]))
            
        except Exception as e:
            logger.error(f"Ошибка получения ответа ИИ: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке запроса. Попробуйте позже."
            )
        
        return 'WAITING_MESSAGE'
    
    def _is_direct_question(self, text: str) -> bool:
        """Определение прямых вопросов, требующих немедленного ответа"""
        text_lower = text.lower()
        
        # Ключевые слова для прямых вопросов
        direct_question_indicators = [
            'что из себя представляет',
            'что входит в',
            'какие курсы',
            'расскажи о',
            'объясни',
            'что такое',
            'как работает',
            'в чем разница',
            'как выбрать',
            'где найти',
            'сколько стоит',
            'как начать',
            'с чего начать',
            'что нужно знать',
            'какие навыки',
            'какие требования'
        ]
        
        # Проверяем наличие прямых вопросов
        for indicator in direct_question_indicators:
            if indicator in text_lower:
                return True
        
        # Проверяем вопросительные знаки в конце
        if text.strip().endswith('?'):
            return True
        
        return False
    
    def _analyze_speech_patterns(self, text: str) -> Dict[str, bool]:
        """Анализ паттернов речи"""
        text_lower = text.lower()
        
        patterns = {
            'psychology_need': False,
            'career_need': False,
            'emotional_support': False,
            'cancellation': False,
            'topic_change': False,
            'self_introduction_request': False,
            'dream_expression': False,
            'provocative': False
        }
        
        # Психологическая помощь
        psychology_keywords = [
            'сон', 'сны', 'депрессия', 'тревога', 'стресс', 'паника', 'страх', 
            'грусть', 'одиночество', 'отношения', 'семья', 'родители', 'дети', 
            'любовь', 'развод', 'смерть', 'потеря', 'плохо', 'больно', 'страшно'
        ]
        patterns['psychology_need'] = any(keyword in text_lower for keyword in psychology_keywords)
        
        # Карьерные вопросы
        career_keywords = [
            'работа', 'карьера', 'профессия', 'зарплата', 'деньги', 'учеба', 
            'образование', 'навыки', 'опыт', 'компания', 'начальник', 'коллеги',
            'высокооплачиваемая работа', 'карьерный рост', 'профессиональное развитие'
        ]
        patterns['career_need'] = any(keyword in text_lower for keyword in career_keywords)
        
        # Эмоциональная поддержка
        emotional_keywords = [
            'одинок', 'грустно', 'плохо', 'устал', 'устала', 'сложно', 'трудно', 
            'помоги', 'поддержка', 'понимаю', 'понимаешь'
        ]
        patterns['emotional_support'] = any(keyword in text_lower for keyword in emotional_keywords)
        
        # Отмена/прекращение
        cancellation_keywords = [
            'не хочу', 'хватит', 'достаточно', 'стоп', 'прекрати', 'остановись', 
            'не буду', 'не буду говорить', 'не хочу говорить', 'хватит говорить'
        ]
        patterns['cancellation'] = any(keyword in text_lower for keyword in cancellation_keywords)
        
        # Смена темы
        topic_change_keywords = [
            'другое', 'другая тема', 'давай о', 'поговорим о', 'хочу поговорить о', 
            'смени тему', 'не об этом'
        ]
        patterns['topic_change'] = any(keyword in text_lower for keyword in topic_change_keywords)
        
        # Запрос рассказать о себе
        self_intro_keywords = [
            'расскажи о себе', 'расскажи о тебе', 'кто ты', 'что ты', 
            'как ты работаешь', 'твоя история', 'твоя работа', 'что ты умеешь'
        ]
        patterns['self_introduction_request'] = any(keyword in text_lower for keyword in self_intro_keywords)
        
        # Мечты и цели
        dream_keywords = [
            'хочу стать', 'мечтаю', 'мечта', 'цель', 'планирую', 'буду', 'стану'
        ]
        patterns['dream_expression'] = any(keyword in text_lower for keyword in dream_keywords)
        
        # Провокационные вопросы
        provocative_keywords = [
            'глупый', 'тупой', 'бесполезный', 'не понимаешь', 'не слушаешь', 
            'плохой', 'ужасный', 'ненавижу', 'ненавидишь', 'не понял', 'не поняла'
        ]
        patterns['provocative'] = any(keyword in text_lower for keyword in provocative_keywords)
        
        return patterns
    
    def _determine_response_type(self, patterns: Dict[str, bool], text: str) -> PromptType:
        """Определение типа ответа"""
        
        if patterns['psychology_need'] or patterns['emotional_support']:
            return PromptType.PSYCHOLOGY_CONSULTATION
        elif patterns['career_need']:
            return PromptType.CAREER_CONSULTATION
        elif 'тест самооценки' in text.lower() or 'восхождение' in text.lower():
            return PromptType.SELF_ESTEEM_ANALYSIS
        elif 'полный анализ' in text.lower() or 'детальный анализ' in text.lower():
            return PromptType.FULL_ANALYSIS
        else:
            return PromptType.EXPRESS_ANALYSIS
    
    async def _get_ai_response(self, user_id: int, message: str, response_type: PromptType) -> str:
        """Получение ответа от ИИ"""
        
        # Формируем контекст
        conversation_context = self.conversation_history.get(user_id, [])
        context = {
            'conversation': '\n'.join(conversation_context),
            'user_message': message,
            'message_count': len(conversation_context)
        }
        
        # Получаем ответ от ИИ
        ai_response = await self.ai_client.get_response(
            prompt=message,
            user_id=user_id,
            prompt_type=response_type,
            context=context
        )
        
        return ai_response.content
    
    async def _send_response(self, update: Update, response: str):
        """Отправка ответа пользователю"""
        
        # Разбиваем длинный ответ на части
        max_length = 4000
        if len(response) <= max_length:
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        else:
            parts = [response[i:i+max_length] for i in range(0, len(response), max_length)]
            for i, part in enumerate(parts):
                prefix = f"**Ответ (часть {i+1}/{len(parts)}):**\n\n" if i > 0 else ""
                await update.message.reply_text(prefix + part, parse_mode=ParseMode.MARKDOWN)
    
    async def _suggest_next_steps(self, update: Update, patterns: Dict[str, bool], message_count: int):
        """Предложение следующих шагов"""
        
        if message_count >= 10 and not patterns['cancellation']:
            # Предлагаем экспресс-анализ
            await update.message.reply_text(
                "💎 **Хотите детальный анализ?**\n\n"
                "Полный психоанализ включает:\n"
                "• 7 профессиональных вопросов\n"
                "• Детальный профиль личности\n"
                "• HR-оценки и рекомендации\n"
                "• Образовательную траекторию\n\n"
                "Стоимость: 500₽\n"
                "Для заказа напишите: 'хочу полный анализ'"
            )
    
    async def _handle_cancellation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка отмены"""
        await update.message.reply_text(
            "Понял. Если захотите поговорить снова - просто напишите. "
            "Я всегда готов выслушать и поддержать. 💙"
        )
        
        # Очищаем данные пользователя
        user = update.effective_user
        self.ai_client.clear_user_data(user.id)
        self.conversation_history.pop(user.id, None)
        
        return 'END'
    
    async def _handle_topic_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка смены темы"""
        await update.message.reply_text(
            "Конечно! О чем бы вы хотели поговорить? "
            "Я готов обсудить любую тему, которая вас интересует. 😊"
        )
        return 'WAITING_MESSAGE'
    
    async def _handle_self_introduction(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка запроса рассказать о себе"""
        await update.message.reply_text(
            "Конечно! Я HR-психоаналитик и карьерный консультант. "
            "Моя работа - помогать людям понять себя, найти свой путь в жизни и карьере. "
            "Я использую методы психоанализа, чтобы лучше понять вашу личность и дать рекомендации. "
            "А теперь расскажите мне о себе! 😊"
        )
        return 'WAITING_MESSAGE'