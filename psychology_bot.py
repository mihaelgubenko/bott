#!/usr/bin/env python3
"""
Улучшенный психологический бот для консультаций по воспитанию детей
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

class TokenManager:
    """Управление токенами и сокращение контекста"""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
    
    def estimate_tokens(self, text: str) -> int:
        """Примерная оценка количества токенов (1 токен ≈ 4 символа)"""
        return len(text) // 4
    
    def compress_context(self, messages: List[Message], max_tokens: int) -> List[Message]:
        """Сжимает контекст, сохраняя важную информацию"""
        if not messages:
            return messages
        
        # Всегда сохраняем последние 2 сообщения
        recent_messages = messages[-2:]
        remaining_tokens = max_tokens - self.estimate_tokens(
            " ".join([msg.content for msg in recent_messages])
        )
        
        if remaining_tokens <= 0:
            return recent_messages
        
        # Добавляем предыдущие сообщения, пока не достигнем лимита
        compressed = []
        for msg in reversed(messages[:-2]):
            msg_tokens = self.estimate_tokens(msg.content)
            if remaining_tokens - msg_tokens >= 0:
                compressed.insert(0, msg)
                remaining_tokens -= msg_tokens
            else:
                break
        
        return compressed + recent_messages

class PsychologyBot:
    """Основной класс психологического бота"""
    
    def __init__(self):
        self.context_manager = ContextManager()
        self.token_manager = TokenManager()
        self.techniques = {
            "дневник_трех_страниц": {
                "name": "Дневник трех страниц",
                "description": "Техника свободного письма для самопознания",
                "steps": [
                    "Возьмите лист бумаги или откройте документ на компьютере",
                    "Напишите три страницы о том, что вас беспокоит в воспитании детей",
                    "Не останавливайтесь и не редактируйте - просто пишите потоком сознания",
                    "После написания прочитайте и выделите ключевые моменты",
                    "Обсудите с партнером или специалистом найденные инсайты"
                ]
            },
            "активное_слушание": {
                "name": "Активное слушание",
                "description": "Техника полного внимания к словам ребенка",
                "steps": [
                    "Полностью сосредоточьтесь на том, что говорит ребенок",
                    "Не перебивайте и не делайте выводы",
                    "Повторите слова ребенка своими словами для проверки понимания",
                    "Спросите: 'Правильно ли я понял, что ты чувствуешь...?'",
                    "Дайте ребенку время выразить свои мысли полностью"
                ]
            },
            "техника_тайм_аута": {
                "name": "Техника тайм-аута",
                "description": "Способ успокоения для родителей и детей",
                "steps": [
                    "При возникновении конфликта сделайте паузу",
                    "Скажите: 'Давайте оба успокоимся и поговорим через 5 минут'",
                    "Используйте это время для глубокого дыхания",
                    "Вернитесь к разговору в спокойном состоянии",
                    "Обсудите проблему конструктивно"
                ]
            }
        }
    
    def extract_user_name(self, message: str) -> str:
        """Извлекает имя пользователя из сообщения"""
        # Ищем паттерн "Имя Фамилия:"
        match = re.search(r'^([А-Яа-я]+\s+[А-Яа-я]+):', message)
        if match:
            return match.group(1)
        return "Пользователь"
    
    def extract_user_content(self, message: str) -> str:
        """Извлекает содержание сообщения пользователя"""
        # Убираем имя пользователя из начала сообщения
        content = re.sub(r'^[А-Яа-я]+\s+[А-Яа-я]+:\s*', '', message)
        return content.strip()
    
    def detect_topic(self, content: str) -> str:
        """Определяет тему сообщения"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['воспитание', 'дети', 'ребенок', 'семья']):
            return "воспитание_детей"
        elif any(word in content_lower for word in ['конфликт', 'ссора', 'проблема']):
            return "конфликты"
        elif any(word in content_lower for word in ['техника', 'метод', 'способ']):
            return "техники_воспитания"
        elif any(word in content_lower for word in ['эмоции', 'чувства', 'переживания']):
            return "эмоциональное_развитие"
        else:
            return "общие_вопросы"
    
    def generate_response(self, user_name: str, user_content: str) -> str:
        """Генерирует ответ бота"""
        # Добавляем сообщение пользователя в контекст
        self.context_manager.add_message(user_name, "user", user_content)
        
        # Получаем контекст диалога
        context = self.context_manager.get_or_create_context(user_name)
        recent_messages = self.context_manager.get_recent_context(user_name, 3)
        
        # Определяем тему
        topic = self.detect_topic(user_content)
        self.context_manager.set_current_topic(user_name, topic)
        
        # Проверяем, есть ли активная техника
        if context.active_technique:
            return self._continue_technique(user_name, user_content, context)
        
        # Анализируем запрос пользователя
        if "техника" in user_content.lower() and "дневник" in user_content.lower():
            return self._start_technique(user_name, "дневник_трех_страниц")
        elif "техника" in user_content.lower() and "слушание" in user_content.lower():
            return self._start_technique(user_name, "активное_слушание")
        elif "помощь" in user_content.lower() or "сложно" in user_content.lower():
            return self._offer_help(user_name, user_content)
        elif "спасибо" in user_content.lower() or "благодарю" in user_content.lower():
            return self._acknowledge_gratitude(user_name)
        else:
            return self._general_response(user_name, user_content, topic)
    
    def _start_technique(self, user_name: str, technique_key: str) -> str:
        """Начинает работу с техникой"""
        technique = self.techniques[technique_key]
        self.context_manager.set_active_technique(user_name, technique_key, 0)
        
        response = f"Отлично! Давайте изучим технику '{technique['name']}'.\n\n"
        response += f"📝 **Описание:** {technique['description']}\n\n"
        response += f"**Шаг 1:** {technique['steps'][0]}\n\n"
        response += "Готовы продолжить? Напишите 'далее' когда будете готовы к следующему шагу."
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _continue_technique(self, user_name: str, user_content: str, context: DialogueContext) -> str:
        """Продолжает работу с активной техникой"""
        technique = self.techniques[context.active_technique]
        
        if "далее" in user_content.lower() or "следующий" in user_content.lower():
            context.technique_step += 1
            if context.technique_step < len(technique['steps']):
                response = f"**Шаг {context.technique_step + 1}:** {technique['steps'][context.technique_step]}\n\n"
                if context.technique_step < len(technique['steps']) - 1:
                    response += "Напишите 'далее' для следующего шага."
                else:
                    response += "Техника завершена! Как вы себя чувствуете после выполнения?"
                    context.active_technique = None
                    context.technique_step = 0
            else:
                response = "Техника завершена! Как вы себя чувствуете после выполнения?"
                context.active_technique = None
                context.technique_step = 0
        else:
            response = f"Вы сейчас изучаете технику '{technique['name']}'.\n\n"
            response += f"**Текущий шаг {context.technique_step + 1}:** {technique['steps'][context.technique_step]}\n\n"
            response += "Напишите 'далее' для продолжения или поделитесь своими мыслями."
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _offer_help(self, user_name: str, user_content: str) -> str:
        """Предлагает помощь"""
        response = "Понимаю, что вам нужна поддержка. Это абсолютно нормально! 💙\n\n"
        response += "Я могу предложить несколько техник, которые помогут в воспитании детей:\n\n"
        response += "1. **Дневник трех страниц** - для самопознания и понимания своих чувств\n"
        response += "2. **Активное слушание** - для лучшего понимания вашего ребенка\n"
        response += "3. **Техника тайм-аута** - для решения конфликтов\n\n"
        response += "Какую технику вы хотели бы изучить? Или расскажите подробнее о том, что вас беспокоит."
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _acknowledge_gratitude(self, user_name: str) -> str:
        """Отвечает на благодарность"""
        response = "Пожалуйста! 😊 Рад, что смог помочь. Если у вас возникнут еще вопросы по воспитанию детей или семейным отношениям, я всегда готов поддержать вас.\n\n"
        response += "Помните: быть родителем - это одна из самых сложных, но и самых важных ролей в жизни. Вы делаете отличную работу!"
        
        self.context_manager.add_message(user_name, "assistant", response)
        return response
    
    def _general_response(self, user_name: str, user_content: str, topic: str) -> str:
        """Общий ответ на основе темы"""
        if topic == "воспитание_детей":
            response = "Воспитание детей - это действительно важная и сложная задача. Каждый родитель сталкивается с вызовами, и это нормально.\n\n"
            response += "Расскажите, пожалуйста, с какими конкретными ситуациями в воспитании вы сталкиваетесь? Это поможет мне лучше понять, как я могу вам помочь."
        elif topic == "конфликты":
            response = "Конфликты в семье - это естественная часть отношений. Важно научиться решать их конструктивно.\n\n"
            response += "Могу предложить технику 'Тайм-аут' для решения конфликтных ситуаций. Хотели бы попробовать?"
        elif topic == "техники_воспитания":
            response = "У меня есть несколько проверенных техник для работы с детьми:\n\n"
            response += "• **Активное слушание** - для понимания ребенка\n"
            response += "• **Дневник трех страниц** - для самоанализа\n"
            response += "• **Техника тайм-аута** - для решения конфликтов\n\n"
            response += "Какую из них вы хотели бы изучить?"
        else:
            response = "Я понимаю, что вам нужна поддержка. Как психологический помощник, я специализируюсь на вопросах воспитания детей и семейных отношений.\n\n"
            response += "Поделитесь, пожалуйста, что именно вас беспокоит или интересует в этой области?"
        
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
    """Демонстрация работы бота"""
    bot = PsychologyBot()
    
    # Тестовые сообщения
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