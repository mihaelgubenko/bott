#!/usr/bin/env python3
"""
Улучшенный психологический бот с лучшим пониманием контекста
Решает проблемы: переключение сценариев, обрывы диалога, потеря контекста
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

@dataclass
class Message:
    """Структура сообщения в диалоге"""
    role: str  # 'user' или 'assistant'
    content: str
    timestamp: str
    message_id: str

@dataclass
class DialogueContext:
    """Контекст диалога с пользователем"""
    user_name: str
    current_topic: str
    conversation_history: List[Message]
    active_technique: Optional[str] = None
    technique_step: int = 0
    session_id: str = ""
    last_user_intent: str = ""

class ContextManager:
    """Управление контекстом диалога"""
    
    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self.contexts: Dict[str, DialogueContext] = {}
    
    def get_or_create_context(self, user_name: str) -> DialogueContext:
        """Получить или создать контекст для пользователя"""
        if user_name not in self.contexts:
            self.contexts[user_name] = DialogueContext(
                user_name=user_name,
                current_topic="",
                conversation_history=[],
                session_id=hashlib.md5(f"{user_name}_{datetime.now()}".encode()).hexdigest()[:8]
            )
        return self.contexts[user_name]
    
    def add_message(self, user_name: str, role: str, content: str):
        """Добавить сообщение в историю"""
        context = self.get_or_create_context(user_name)
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            message_id=hashlib.md5(f"{user_name}_{content}_{datetime.now()}".encode()).hexdigest()[:8]
        )
        context.conversation_history.append(message)
        
        # Ограничиваем размер истории
        if len(context.conversation_history) > self.max_history:
            context.conversation_history = context.conversation_history[-self.max_history:]
    
    def get_recent_context(self, user_name: str, last_n: int = 5) -> List[Message]:
        """Получить последние N сообщений для контекста"""
        context = self.get_or_create_context(user_name)
        return context.conversation_history[-last_n:] if context.conversation_history else []
    
    def set_current_topic(self, user_name: str, topic: str):
        """Установить текущую тему разговора"""
        context = self.get_or_create_context(user_name)
        context.current_topic = topic
    
    def set_active_technique(self, user_name: str, technique: str, step: int = 0):
        """Установить активную технику"""
        context = self.get_or_create_context(user_name)
        context.active_technique = technique
        context.technique_step = step
    
    def set_last_intent(self, user_name: str, intent: str):
        """Установить последнее намерение пользователя"""
        context = self.get_or_create_context(user_name)
        context.last_user_intent = intent

class ImprovedPsychologyBot:
    """Улучшенный психологический бот с лучшим пониманием контекста"""
    
    def __init__(self):
        self.context_manager = ContextManager()
        self.techniques = {
            "дневник_трех_страниц": {
                "name": "Дневник трех страниц",
                "description": "Техника свободного письма для самопознания и понимания своих чувств",
                "steps": [
                    "Возьмите лист бумаги или откройте документ на компьютере",
                    "Напишите три страницы о том, что вас беспокоит в воспитании детей. Не останавливайтесь и не редактируйте - просто пишите потоком сознания",
                    "После написания прочитайте и выделите ключевые моменты и эмоции",
                    "Попробуйте найти закономерности в своих мыслях и чувствах",
                    "Обсудите найденные инсайты с партнером или специалистом"
                ]
            },
            "активное_слушание": {
                "name": "Активное слушание",
                "description": "Техника полного внимания к словам и чувствам ребенка",
                "steps": [
                    "Полностью сосредоточьтесь на том, что говорит ребенок. Уберите все отвлекающие факторы",
                    "Не перебивайте и не делайте выводы. Дайте ребенку полностью высказаться",
                    "Повторите слова ребенка своими словами: 'Правильно ли я понял, что ты чувствуешь...?'",
                    "Спросите о чувствах: 'Что ты чувствуешь, когда это происходит?'",
                    "Поблагодарите ребенка за то, что он поделился с вами"
                ]
            },
            "техника_тайм_аута": {
                "name": "Техника тайм-аута",
                "description": "Способ успокоения для родителей и детей в конфликтных ситуациях",
                "steps": [
                    "При возникновении конфликта сделайте паузу и скажите: 'Давайте оба успокоимся'",
                    "Уйдите в разные комнаты на 5-10 минут. Используйте это время для глубокого дыхания",
                    "Вернитесь к разговору в спокойном состоянии",
                    "Начните с извинений и обсудите проблему конструктивно",
                    "Вместе найдите решение, которое устроит обе стороны"
                ]
            }
        }
    
    def extract_user_name(self, message: str) -> str:
        """Извлекает имя пользователя из сообщения"""
        match = re.search(r'^([А-Яа-я]+\s+[А-Яа-я]+):', message)
        if match:
            return match.group(1)
        return "Пользователь"
    
    def extract_user_content(self, message: str) -> str:
        """Извлекает содержание сообщения пользователя"""
        content = re.sub(r'^[А-Яа-я]+\s+[А-Яа-я]+:\s*', '', message)
        return content.strip()
    
    def analyze_user_intent(self, content: str, context: DialogueContext) -> str:
        """Анализирует намерение пользователя с учетом контекста"""
        content_lower = content.lower()
        
        # Если есть активная техника, проверяем команды для неё
        if context.active_technique:
            if any(word in content_lower for word in ['далее', 'следующий', 'продолжить', 'продолжи']):
                return "continue_technique"
            elif any(word in content_lower for word in ['стоп', 'остановить', 'хватит']):
                return "stop_technique"
            else:
                return "technique_feedback"
        
        # Анализируем новые запросы
        if any(word in content_lower for word in ['техника', 'метод', 'способ']):
            if 'дневник' in content_lower:
                return "request_diary_technique"
            elif 'слушание' in content_lower or 'слушать' in content_lower:
                return "request_listening_technique"
            elif 'тайм' in content_lower or 'тайм-аут' in content_lower:
                return "request_timeout_technique"
            else:
                return "request_any_technique"
        
        if any(word in content_lower for word in ['помощь', 'помоги', 'сложно', 'трудно']):
            return "request_help"
        
        if any(word in content_lower for word in ['спасибо', 'благодарю', 'спасибо большое']):
            return "gratitude"
        
        if any(word in content_lower for word in ['извини', 'прости', 'не понял', 'вернись']):
            return "clarification_request"
        
        if any(word in content_lower for word in ['согласен', 'да', 'хорошо', 'ок']):
            return "agreement"
        
        return "general_inquiry"
    
    def generate_response(self, user_name: str, user_content: str) -> str:
        """Генерирует ответ бота с учетом контекста"""
        # Добавляем сообщение пользователя в контекст
        self.context_manager.add_message(user_name, "user", user_content)
        
        # Получаем контекст диалога
        context = self.context_manager.get_or_create_context(user_name)
        
        # Анализируем намерение пользователя
        intent = self.analyze_user_intent(user_content, context)
        self.context_manager.set_last_intent(user_name, intent)
        
        # Генерируем ответ на основе намерения
        if intent == "request_diary_technique":
            return self._start_technique(user_name, "дневник_трех_страниц")
        elif intent == "request_listening_technique":
            return self._start_technique(user_name, "активное_слушание")
        elif intent == "request_timeout_technique":
            return self._start_technique(user_name, "техника_тайм_аута")
        elif intent == "request_any_technique":
            return self._offer_techniques(user_name)
        elif intent == "continue_technique":
            return self._continue_technique(user_name, context)
        elif intent == "stop_technique":
            return self._stop_technique(user_name, context)
        elif intent == "technique_feedback":
            return self._handle_technique_feedback(user_name, user_content, context)
        elif intent == "request_help":
            return self._offer_help(user_name, user_content)
        elif intent == "gratitude":
            return self._acknowledge_gratitude(user_name)
        elif intent == "clarification_request":
            return self._handle_clarification_request(user_name, context)
        elif intent == "agreement":
            return self._handle_agreement(user_name, context)
        else:
            return self._general_response(user_name, user_content, context)
    
    def _start_technique(self, user_name: str, technique_key: str) -> str:
        """Начинает работу с техникой"""
        technique = self.techniques[technique_key]
        self.context_manager.set_active_technique(user_name, technique_key, 0)
        
        response = f"Отлично! Давайте изучим технику **'{technique['name']}'**. 📝\n\n"
        response += f"**Описание:** {technique['description']}\n\n"
        response += f"**Шаг 1 из {len(technique['steps'])}:** {technique['steps'][0]}\n\n"
        response += "Когда будете готовы к следующему шагу, напишите **'далее'**."
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _continue_technique(self, user_name: str, context: DialogueContext) -> str:
        """Продолжает работу с активной техникой"""
        technique = self.techniques[context.active_technique]
        context.technique_step += 1
        
        if context.technique_step < len(technique['steps']):
            response = f"**Шаг {context.technique_step + 1} из {len(technique['steps'])}:** {technique['steps'][context.technique_step]}\n\n"
            if context.technique_step < len(technique['steps']) - 1:
                response += "Напишите **'далее'** для следующего шага."
            else:
                response += "🎉 **Техника завершена!** Как вы себя чувствуете после выполнения? Поделитесь своими впечатлениями."
                context.active_technique = None
                context.technique_step = 0
        else:
            response = "Техника уже завершена! Как вы себя чувствуете после выполнения?"
            context.active_technique = None
            context.technique_step = 0
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _stop_technique(self, user_name: str, context: DialogueContext) -> str:
        """Останавливает работу с техникой"""
        technique_name = self.techniques[context.active_technique]['name']
        context.active_technique = None
        context.technique_step = 0
        
        response = f"Хорошо, мы остановили изучение техники '{technique_name}'. "
        response += "Если захотите вернуться к ней позже или изучить другую технику, просто скажите мне!"
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _handle_technique_feedback(self, user_name: str, user_content: str, context: DialogueContext) -> str:
        """Обрабатывает обратную связь по технике"""
        response = "Спасибо, что поделились своими мыслями! 💭\n\n"
        
        if context.active_technique:
            technique = self.techniques[context.active_technique]
            response += f"Вы сейчас изучаете технику '{technique['name']}'. "
            response += f"**Текущий шаг {context.technique_step + 1}:** {technique['steps'][context.technique_step]}\n\n"
            response += "Напишите **'далее'** для продолжения или поделитесь дополнительными мыслями."
        else:
            response += "Хотели бы изучить какую-то конкретную технику воспитания?"
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _offer_techniques(self, user_name: str) -> str:
        """Предлагает доступные техники"""
        response = "У меня есть несколько проверенных техник для работы с детьми и семьей:\n\n"
        response += "1. **Дневник трех страниц** - для самопознания и понимания своих чувств\n"
        response += "2. **Активное слушание** - для лучшего понимания вашего ребенка\n"
        response += "3. **Техника тайм-аута** - для решения конфликтов\n\n"
        response += "Какую технику вы хотели бы изучить? Просто скажите название или номер."
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _offer_help(self, user_name: str, user_content: str) -> str:
        """Предлагает помощь"""
        response = "Понимаю, что вам нужна поддержка. Это абсолютно нормально! 💙\n\n"
        response += "Воспитание детей - одна из самых важных и сложных задач в жизни. "
        response += "Я здесь, чтобы помочь вам найти подходящие инструменты и техники.\n\n"
        response += "Могу предложить:\n"
        response += "• **Техники воспитания** - конкретные методы работы с детьми\n"
        response += "• **Советы по решению конфликтов** - как справляться со сложными ситуациями\n"
        response += "• **Поддержку в самопознании** - понимание своих эмоций и реакций\n\n"
        response += "Что вас больше всего интересует или беспокоит?"
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _acknowledge_gratitude(self, user_name: str) -> str:
        """Отвечает на благодарность"""
        response = "Пожалуйста! 😊 Рад, что смог помочь. "
        response += "Помните: быть родителем - это постоянное обучение и рост. "
        response += "Вы делаете отличную работу, заботясь о своих детях!\n\n"
        response += "Если у вас возникнут еще вопросы по воспитанию или семейным отношениям, "
        response += "я всегда готов поддержать вас."
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _handle_clarification_request(self, user_name: str, context: DialogueContext) -> str:
        """Обрабатывает запрос на уточнение"""
        if context.active_technique:
            technique = self.techniques[context.active_technique]
            response = f"Конечно! Мы изучаем технику **'{technique['name']}'**.\n\n"
            response += f"**Описание:** {technique['description']}\n\n"
            response += f"**Текущий шаг {context.technique_step + 1}:** {technique['steps'][context.technique_step]}\n\n"
            response += "Напишите **'далее'** для продолжения."
        else:
            response = "Конечно! Давайте вернемся к вашему вопросу о психологической помощи в воспитании детей.\n\n"
            response += "Я могу предложить несколько техник, которые помогут вам лучше понимать своих детей "
            response += "и справляться с различными ситуациями в семье.\n\n"
            response += "Какую область вас больше всего интересует?"
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _handle_agreement(self, user_name: str, context: DialogueContext) -> str:
        """Обрабатывает согласие пользователя"""
        if context.last_user_intent == "request_any_technique":
            return self._offer_techniques(user_name)
        else:
            response = "Отлично! Я рад, что вы готовы работать над улучшением отношений в семье.\n\n"
            response += "С чего бы вы хотели начать? Могу предложить несколько техник воспитания."
            self.context_manager.add_message(user_name, "assistant", response)
            return response
    
    def _general_response(self, user_name: str, user_content: str, context: DialogueContext) -> str:
        """Общий ответ на основе контекста"""
        response = "Понимаю, что вам нужна поддержка в вопросах воспитания детей. "
        response += "Это действительно важная и сложная задача, и я здесь, чтобы помочь вам.\n\n"
        response += "Расскажите, пожалуйста, с какими конкретными ситуациями в воспитании "
        response += "вы сталкиваетесь? Или какие техники вас интересуют?"
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def process_message(self, message: str) -> str:
        """Основной метод обработки сообщения"""
        try:
            # Извлекаем имя пользователя и содержание
            user_name = self.extract_user_name(message)
            user_content = self.extract_user_content(message)
            
            # Генерируем ответ
            response = self.generate_response(user_name, user_content)
            
            return response
            
        except Exception as e:
            return f"Извините, произошла ошибка при обработке вашего сообщения: {str(e)}. Попробуйте еще раз."

def main():
    """Демонстрация работы улучшенного бота"""
    bot = ImprovedPsychologyBot()
    
    # Тестовые сообщения из вашего диалога
    test_messages = [
        "Михаил Губенко: Привет, я бы хотел получить психологическую помощь в вопросах воспитания детей и семьи. Как ты можешь помочь мне в этом",
        "Михаил Губенко: Мне немного сложно объяснить, я бы предпочёл находящиеся вопросы, известные тебе по психологии или из иных источников...",
        "Михаил Губенко: Хорошо, я согласен, опиши мне в вкратце эту технику",
        "Михаил Губенко: Извини, ты меня не понял, вернись к предыдущему вопросу"
    ]
    
    print("=== Демонстрация работы улучшенного психологического бота ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"Сообщение {i}: {message}")
        response = bot.process_message(message)
        print(f"Ответ бота: {response}")
        print("-" * 80)

if __name__ == "__main__":
    main()