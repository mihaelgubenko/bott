#!/usr/bin/env python3
"""
Простая демонстрация работы улучшенного психологического бота
"""

from final_psychology_bot import FinalPsychologyBot

def main():
    """Интерактивная демонстрация бота"""
    bot = FinalPsychologyBot()
    
    print("=" * 80)
    print("🧠 ПСИХОЛОГИЧЕСКИЙ ПОМОЩНИК")
    print("Консультации по воспитанию детей и семейным отношениям")
    print("=" * 80)
    print()
    print("Добро пожаловать! Я помогу вам с вопросами воспитания детей.")
    print("Просто напишите ваш вопрос или проблему.")
    print("Для выхода введите 'выход' или 'quit'")
    print("Для сброса контекста введите 'сброс' или 'reset'")
    print()
    
    while True:
        try:
            # Получаем ввод пользователя
            user_input = input("Вы: ").strip()
            
            # Проверяем команды выхода
            if user_input.lower() in ['выход', 'quit', 'exit', 'q']:
                print("\nДо свидания! Удачи в воспитании детей! 👋")
                break
            
            # Проверяем команду сброса
            if user_input.lower() in ['сброс', 'reset', 'очистить']:
                bot = FinalPsychologyBot()
                print("\n✅ Контекст диалога сброшен!")
                print("Добро пожаловать! Я помогу вам с вопросами воспитания детей.")
                continue
            
            # Пропускаем пустые сообщения
            if not user_input:
                continue
            
            # Обрабатываем сообщение ботом
            response = bot.process_message(user_input)
            
            # Выводим ответ
            print(f"\nБот: {response}")
            print("-" * 80)
            
        except KeyboardInterrupt:
            print("\n\nДо свидания! Удачи в воспитании детей! 👋")
            break
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            print("Попробуйте еще раз или введите 'сброс' для сброса контекста.")

if __name__ == "__main__":
    main()