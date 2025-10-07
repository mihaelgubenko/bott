"""
Менеджер консультаций и состояний диалога
Управляет сессиями консультаций, лимитами, тарифами и состояниями бота
"""

import sqlite3
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# ТИПЫ И ПЕРЕЧИСЛЕНИЯ
# ============================================================================

class DialogState(Enum):
    """Состояния диалога"""
    INITIAL = "initial"                    # Только начали
    CHOOSING_CONSULTATION = "choosing"     # Выбор типа консультации
    CHOOSING_TIER = "choosing_tier"        # Выбор тарифа
    IN_CONSULTATION = "in_consultation"    # Идет консультация  
    EXPRESS_ANALYSIS = "express_analysis"  # Накопление для анализа
    FULL_ANALYSIS = "full_analysis"        # Платный анализ
    SESSION_ENDING = "session_ending"      # Завершение сессии


class ConsultationType(Enum):
    """Типы консультаций"""
    FAMILY = "family"                      # Семья, дети, воспитание
    CAREER = "career"                      # Карьера, работа
    EMOTIONAL = "emotional"                # Стресс, тревога, депрессия
    RELATIONSHIPS = "relationships"        # Личные отношения
    SELF_DEVELOPMENT = "self_development"  # Саморазвитие, цели
    GENERAL = "general"                    # Общая консультация


class SessionTier(Enum):
    """Тарифы консультаций"""
    FREE = "free"          # Бесплатно
    STANDARD = "standard"  # 500₽
    PREMIUM = "premium"    # 1000₽


# ============================================================================
# КОНФИГУРАЦИЯ ЛИМИТОВ
# ============================================================================

CONSULTATION_LIMITS = {
    SessionTier.FREE: {
        'duration_minutes': 25,
        'max_messages': 10,
        'max_tokens_per_response': 500,   # Увеличено с 300
        'total_tokens_budget': 5000,      # ~5000 токенов на сессию
        'price': 0,
        'name': '🆓 Экспресс-консультация',
        'description': 'Базовая поддержка и короткие практические советы'
    },
    SessionTier.STANDARD: {
        'duration_minutes': 45,
        'max_messages': 30,
        'max_tokens_per_response': 800,   # Подробные ответы
        'total_tokens_budget': 24000,     # ~24k токенов
        'price': 500,
        'name': '💎 Расширенная консультация',
        'description': 'Глубокий анализ, детальные техники, индивидуальный план'
    },
    SessionTier.PREMIUM: {
        'duration_minutes': 90,
        'max_messages': 100,              # Практически безлимит
        'max_tokens_per_response': 1500,  # Очень подробно
        'total_tokens_budget': 50000,     # ~50k токенов
        'price': 1000,
        'name': '💼 Профессиональная сессия',
        'description': 'Полноценная психологическая сессия с глубинной работой'
    }
}


# ============================================================================
# КЛЮЧЕВЫЕ СЛОВА ДЛЯ ОПРЕДЕЛЕНИЯ ТИПА КОНСУЛЬТАЦИИ
# ============================================================================

CONSULTATION_KEYWORDS = {
    ConsultationType.FAMILY: [
        'семья', 'дети', 'ребенок', 'дочь', 'сын', 'подросток',
        'муж', 'жена', 'родители', 'воспитание', 'мама', 'папа',
        'брат', 'сестра', 'бабушка', 'дедушка', 'супруг', 'супруга',
        'развод', 'конфликт в семье', 'семейные отношения'
    ],
    ConsultationType.CAREER: [
        'работа', 'карьера', 'босс', 'начальник', 'коллеги', 'коллектив',
        'зарплата', 'увольнение', 'повышение', 'вакансия', 'резюме',
        'собеседование', 'профессия', 'компания', 'офис', 'проект'
    ],
    ConsultationType.EMOTIONAL: [
        'стресс', 'тревога', 'депрессия', 'паника', 'страх', 'фобия',
        'грусть', 'плохо', 'тяжело', 'больно', 'устал', 'устала',
        'выгорание', 'апатия', 'бессонница', 'кошмары', 'нервы'
    ],
    ConsultationType.RELATIONSHIPS: [
        'отношения', 'парень', 'девушка', 'любовь', 'расставание',
        'измена', 'ревность', 'знакомства', 'свидание', 'партнер',
        'одиночество', 'друзья', 'дружба', 'конфликт', 'ссора'
    ],
    ConsultationType.SELF_DEVELOPMENT: [
        'саморазвитие', 'самореализация', 'цели', 'мечта', 'мечтаю',
        'хочу стать', 'планирую', 'развитие', 'учеба', 'образование',
        'навыки', 'потенциал', 'мотивация', 'уверенность'
    ]
}


# ============================================================================
# СТРУКТУРЫ ДАННЫХ
# ============================================================================

@dataclass
class ConsultationSession:
    """Сессия консультации"""
    session_id: str
    user_id: int
    consultation_type: ConsultationType
    tier: SessionTier
    
    # Лимиты
    max_duration_minutes: int
    max_messages: int
    max_tokens_per_response: int
    total_tokens_budget: int
    
    # Текущее состояние
    start_time: datetime
    messages_used: int = 0
    tokens_used: int = 0
    
    # Статус
    is_active: bool = True
    warning_sent: bool = False
    
    # Оплата
    payment_status: str = 'pending'  # pending, paid, free
    amount_paid: float = 0.0
    
    # Дополнительная информация
    topic: str = ""  # Краткое описание темы консультации
    end_time: Optional[datetime] = None


@dataclass
class UserDialogContext:
    """Контекст диалога пользователя"""
    user_id: int
    current_state: DialogState
    active_session: Optional[ConsultationSession] = None
    pending_consultation_type: Optional[ConsultationType] = None
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.last_activity is None:
            self.last_activity = datetime.now()


# ============================================================================
# МЕНЕДЖЕР КОНСУЛЬТАЦИЙ
# ============================================================================

class ConsultationManager:
    """Управление консультациями и состояниями диалога"""
    
    def __init__(self, db_path: str = 'psychoanalyst.db'):
        self.db_path = db_path
        self.init_database()
        
        # Хранилище контекстов диалогов в памяти
        self._dialog_contexts: Dict[int, UserDialogContext] = {}
    
    def init_database(self):
        """Инициализация таблиц БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица сессий консультаций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                consultation_type TEXT NOT NULL,
                tier TEXT NOT NULL,
                
                max_duration_minutes INTEGER,
                max_messages INTEGER,
                max_tokens_per_response INTEGER,
                total_tokens_budget INTEGER,
                
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                messages_used INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                
                is_active BOOLEAN DEFAULT TRUE,
                warning_sent BOOLEAN DEFAULT FALSE,
                
                payment_status TEXT DEFAULT 'pending',
                amount_paid REAL DEFAULT 0.0,
                
                topic TEXT,
                
                FOREIGN KEY (user_id) REFERENCES clients (telegram_id)
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_active_sessions 
            ON consultation_sessions(user_id, is_active)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_start_time 
            ON consultation_sessions(start_time)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Consultation database initialized")
    
    # ========================================================================
    # УПРАВЛЕНИЕ КОНТЕКСТОМ ДИАЛОГА
    # ========================================================================
    
    def get_dialog_context(self, user_id: int) -> UserDialogContext:
        """Получить контекст диалога пользователя"""
        if user_id not in self._dialog_contexts:
            self._dialog_contexts[user_id] = UserDialogContext(
                user_id=user_id,
                current_state=DialogState.INITIAL
            )
        
        # Обновляем время последней активности
        self._dialog_contexts[user_id].last_activity = datetime.now()
        
        return self._dialog_contexts[user_id]
    
    def set_dialog_state(self, user_id: int, state: DialogState):
        """Установить состояние диалога"""
        context = self.get_dialog_context(user_id)
        context.current_state = state
        logger.info(f"User {user_id} dialog state: {state.value}")
    
    def clear_dialog_context(self, user_id: int):
        """Очистить контекст диалога"""
        if user_id in self._dialog_contexts:
            del self._dialog_contexts[user_id]
    
    # ========================================================================
    # ОПРЕДЕЛЕНИЕ ТИПА КОНСУЛЬТАЦИИ
    # ========================================================================
    
    def detect_consultation_type(self, text: str, history: List[str] = None) -> Tuple[ConsultationType, float]:
        """
        Определить тип консультации по тексту и истории
        
        Returns:
            (consultation_type, confidence) - тип и уверенность (0-1)
        """
        text_lower = text.lower()
        all_text = text_lower
        
        # Добавляем историю для более точного определения
        if history:
            recent_history = ' '.join(history[-5:]).lower()  # Последние 5 сообщений
            all_text = recent_history + ' ' + text_lower
        
        # Подсчитываем совпадения для каждого типа
        scores = {}
        for cons_type, keywords in CONSULTATION_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in all_text)
            if score > 0:
                scores[cons_type] = score
        
        # Если ничего не найдено - общая консультация
        if not scores:
            return ConsultationType.GENERAL, 0.5
        
        # Находим тип с максимальным скором
        best_type = max(scores.items(), key=lambda x: x[1])
        
        # Вычисляем уверенность (нормализуем от 0 до 1)
        max_score = best_type[1]
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.5
        
        return best_type[0], min(confidence, 0.95)  # Максимум 0.95
    
    # ========================================================================
    # УПРАВЛЕНИЕ СЕССИЯМИ
    # ========================================================================
    
    def create_session(self, user_id: int, consultation_type: ConsultationType, 
                      tier: SessionTier, topic: str = "") -> ConsultationSession:
        """Создать новую сессию консультации"""
        
        # Получаем лимиты для тарифа
        limits = CONSULTATION_LIMITS[tier]
        
        # Создаем сессию
        session = ConsultationSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            consultation_type=consultation_type,
            tier=tier,
            max_duration_minutes=limits['duration_minutes'],
            max_messages=limits['max_messages'],
            max_tokens_per_response=limits['max_tokens_per_response'],
            total_tokens_budget=limits['total_tokens_budget'],
            start_time=datetime.now(),
            payment_status='free' if tier == SessionTier.FREE else 'pending',
            amount_paid=limits['price'],
            topic=topic
        )
        
        # Сохраняем в БД
        self._save_session_to_db(session)
        
        # Обновляем контекст диалога
        context = self.get_dialog_context(user_id)
        context.active_session = session
        context.current_state = DialogState.IN_CONSULTATION
        
        logger.info(f"Created session {session.session_id} for user {user_id}: "
                   f"{consultation_type.value} ({tier.value})")
        
        return session
    
    def get_active_session(self, user_id: int) -> Optional[ConsultationSession]:
        """Получить активную сессию пользователя"""
        
        # Сначала проверяем в контексте
        context = self.get_dialog_context(user_id)
        if context.active_session and context.active_session.is_active:
            return context.active_session
        
        # Иначе ищем в БД
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM consultation_sessions 
            WHERE user_id = ? AND is_active = TRUE 
            ORDER BY start_time DESC LIMIT 1
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            session = self._row_to_session(row)
            # Обновляем контекст
            context.active_session = session
            return session
        
        return None
    
    def update_session_usage(self, session: ConsultationSession, 
                            messages_delta: int = 0, tokens_delta: int = 0):
        """Обновить использование ресурсов сессии"""
        session.messages_used += messages_delta
        session.tokens_used += tokens_delta
        
        # Сохраняем в БД
        self._update_session_in_db(session)
    
    def end_session(self, session: ConsultationSession, reason: str = "completed"):
        """Завершить сессию"""
        session.is_active = False
        session.end_time = datetime.now()
        
        # Сохраняем в БД
        self._update_session_in_db(session)
        
        # Обновляем контекст
        context = self.get_dialog_context(session.user_id)
        context.active_session = None
        context.current_state = DialogState.SESSION_ENDING
        
        logger.info(f"Session {session.session_id} ended: {reason}")
    
    # ========================================================================
    # ПРОВЕРКА ЛИМИТОВ
    # ========================================================================
    
    def check_session_limits(self, session: ConsultationSession) -> Dict:
        """
        Проверить лимиты сессии
        
        Returns:
            {
                'should_warn': bool,
                'should_end': bool,
                'messages_remaining': int,
                'time_remaining': float (minutes),
                'tokens_remaining': int,
                'limiting_factor': str
            }
        """
        elapsed = (datetime.now() - session.start_time).total_seconds() / 60
        time_remaining = session.max_duration_minutes - elapsed
        messages_remaining = session.max_messages - session.messages_used
        tokens_remaining = session.total_tokens_budget - session.tokens_used
        
        # Определяем лимитирующий фактор
        limits = {
            'time': time_remaining / session.max_duration_minutes,
            'messages': messages_remaining / session.max_messages,
            'tokens': tokens_remaining / session.total_tokens_budget
        }
        limiting_factor = min(limits.items(), key=lambda x: x[1])
        
        # Проверяем условия для окончания
        should_end = (
            messages_remaining <= 0 or
            time_remaining <= 0 or
            tokens_remaining <= 0
        )
        
        # Проверяем условия для предупреждения (20% остатка)
        should_warn = (
            not session.warning_sent and
            not should_end and
            limiting_factor[1] <= 0.2  # 20% или меньше
        )
        
        return {
            'should_warn': should_warn,
            'should_end': should_end,
            'messages_remaining': max(0, messages_remaining),
            'time_remaining': max(0, time_remaining),
            'tokens_remaining': max(0, tokens_remaining),
            'limiting_factor': limiting_factor[0]
        }
    
    def mark_warning_sent(self, session: ConsultationSession):
        """Отметить, что предупреждение отправлено"""
        session.warning_sent = True
        self._update_session_in_db(session)
    
    # ========================================================================
    # АДАПТИВНОЕ УПРАВЛЕНИЕ ТОКЕНАМИ
    # ========================================================================
    
    def get_adaptive_max_tokens(self, session: ConsultationSession, 
                               message_length: int = 0) -> int:
        """
        Определить max_tokens в зависимости от:
        1. Тарифа сессии
        2. Длины вопроса (сложности)
        3. Оставшегося бюджета токенов
        """
        base_limit = session.max_tokens_per_response
        tokens_remaining = session.total_tokens_budget - session.tokens_used
        
        # Определяем сложность по длине сообщения
        if message_length < 50:
            complexity = 0.7  # Простой вопрос
        elif message_length < 150:
            complexity = 1.0  # Средний вопрос
        else:
            complexity = 1.3  # Сложный вопрос
        
        # Вычисляем итоговый лимит
        calculated_tokens = int(base_limit * complexity)
        
        # Не превышаем оставшийся бюджет и не более 150% базового лимита
        max_allowed = min(
            tokens_remaining,
            int(base_limit * 1.5),
            2000  # Абсолютный максимум
        )
        
        return max(min(calculated_tokens, max_allowed), 100)  # Минимум 100 токенов
    
    # ========================================================================
    # ФОРМАТИРОВАНИЕ СООБЩЕНИЙ
    # ========================================================================
    
    def get_session_status_bar(self, session: ConsultationSession) -> str:
        """Создать статус-бар сессии"""
        limits_info = self.check_session_limits(session)
        
        # Эмодзи прогресса
        msg_progress = session.messages_used / session.max_messages
        time_progress = 1 - (limits_info['time_remaining'] / session.max_duration_minutes)
        
        msg_emoji = "🟢" if msg_progress < 0.5 else "🟡" if msg_progress < 0.8 else "🔴"
        time_emoji = "🟢" if time_progress < 0.5 else "🟡" if time_progress < 0.8 else "🔴"
        
        tier_name = CONSULTATION_LIMITS[session.tier]['name']
        
        return f"""
┌─────────────────────────────────────┐
│ {tier_name}
│ {msg_emoji} Сообщений: {session.messages_used}/{session.max_messages}
│ {time_emoji} Времени: ~{int(limits_info['time_remaining'])} мин
└─────────────────────────────────────┘
"""
    
    def get_tier_selection_message(self, consultation_type: ConsultationType) -> str:
        """Сообщение с выбором тарифа"""
        
        type_names = {
            ConsultationType.FAMILY: "семейной психологии",
            ConsultationType.CAREER: "карьерному консультированию",
            ConsultationType.EMOTIONAL: "эмоциональной поддержке",
            ConsultationType.RELATIONSHIPS: "отношениям",
            ConsultationType.SELF_DEVELOPMENT: "саморазвитию",
            ConsultationType.GENERAL: "общей консультации"
        }
        
        type_name = type_names.get(consultation_type, "консультации")
        
        message = f"Я могу провести консультацию по **{type_name}**.\n\n"
        message += "Выберите формат:\n\n"
        
        for tier in [SessionTier.FREE, SessionTier.STANDARD, SessionTier.PREMIUM]:
            limits = CONSULTATION_LIMITS[tier]
            price_str = "Бесплатно" if tier == SessionTier.FREE else f"{limits['price']}₽"
            
            message += f"**{limits['name']}** - {price_str}\n"
            message += f"• {limits['duration_minutes']} минут\n"
            message += f"• До {limits['max_messages']} сообщений\n"
            message += f"• {limits['description']}\n\n"
        
        message += "Напишите номер (1, 2 или 3) или название тарифа."
        
        return message
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ БД
    # ========================================================================
    
    def _save_session_to_db(self, session: ConsultationSession):
        """Сохранить сессию в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO consultation_sessions 
            (session_id, user_id, consultation_type, tier,
             max_duration_minutes, max_messages, max_tokens_per_response, total_tokens_budget,
             start_time, messages_used, tokens_used, is_active, warning_sent,
             payment_status, amount_paid, topic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id, session.user_id, session.consultation_type.value, 
            session.tier.value, session.max_duration_minutes, session.max_messages,
            session.max_tokens_per_response, session.total_tokens_budget,
            session.start_time, session.messages_used, session.tokens_used,
            session.is_active, session.warning_sent,
            session.payment_status, session.amount_paid, session.topic
        ))
        
        conn.commit()
        conn.close()
    
    def _update_session_in_db(self, session: ConsultationSession):
        """Обновить сессию в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE consultation_sessions 
            SET messages_used = ?, tokens_used = ?, is_active = ?, 
                warning_sent = ?, end_time = ?
            WHERE session_id = ?
        ''', (
            session.messages_used, session.tokens_used, session.is_active,
            session.warning_sent, session.end_time, session.session_id
        ))
        
        conn.commit()
        conn.close()
    
    def _row_to_session(self, row) -> ConsultationSession:
        """Преобразовать строку БД в объект сессии"""
        return ConsultationSession(
            session_id=row[0],
            user_id=row[1],
            consultation_type=ConsultationType(row[2]),
            tier=SessionTier(row[3]),
            max_duration_minutes=row[4],
            max_messages=row[5],
            max_tokens_per_response=row[6],
            total_tokens_budget=row[7],
            start_time=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
            end_time=datetime.fromisoformat(row[9]) if row[9] and isinstance(row[9], str) else row[9],
            messages_used=row[10],
            tokens_used=row[11],
            is_active=bool(row[12]),
            warning_sent=bool(row[13]),
            payment_status=row[14],
            amount_paid=row[15],
            topic=row[16] if len(row) > 16 else ""
        )
    
    # ========================================================================
    # СТАТИСТИКА
    # ========================================================================
    
    def get_user_sessions_stats(self, user_id: int) -> Dict:
        """Получить статистику сессий пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                SUM(CASE WHEN tier = 'free' THEN 1 ELSE 0 END) as free_sessions,
                SUM(CASE WHEN tier != 'free' THEN 1 ELSE 0 END) as paid_sessions,
                SUM(amount_paid) as total_paid
            FROM consultation_sessions 
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'total_sessions': row[0] or 0,
            'free_sessions': row[1] or 0,
            'paid_sessions': row[2] or 0,
            'total_paid': row[3] or 0.0
        }


# ============================================================================
# ФАБРИЧНАЯ ФУНКЦИЯ
# ============================================================================

def get_consultation_manager(db_path: str = 'psychoanalyst.db') -> ConsultationManager:
    """Получить менеджер консультаций"""
    return ConsultationManager(db_path)


# ============================================================================
# ТЕСТИРОВАНИЕ
# ============================================================================

if __name__ == "__main__":
    # Тестирование менеджера
    manager = get_consultation_manager()
    
    # Определение типа консультации
    test_messages = [
        "Моя дочь 16 лет все время зовет подружек домой",
        "Я хочу сменить работу, но не знаю что выбрать",
        "У меня сильный стресс и я не могу спать"
    ]
    
    for msg in test_messages:
        cons_type, confidence = manager.detect_consultation_type(msg)
        print(f"Сообщение: '{msg}'")
        print(f"  → Тип: {cons_type.value}, уверенность: {confidence:.2f}\n")
    
    # Создание сессии
    session = manager.create_session(
        user_id=12345,
        consultation_type=ConsultationType.FAMILY,
        tier=SessionTier.FREE,
        topic="воспитание подростка"
    )
    print(f"Создана сессия: {session.session_id}")
    print(f"Лимиты: {session.max_messages} сообщений, {session.max_duration_minutes} минут")
    
    # Проверка лимитов
    limits = manager.check_session_limits(session)
    print(f"\nСтатус лимитов:")
    print(f"  Сообщений осталось: {limits['messages_remaining']}")
    print(f"  Времени осталось: {limits['time_remaining']:.1f} мин")
    print(f"  Токенов осталось: {limits['tokens_remaining']}")
    
    print("\n✅ Менеджер консультаций работает корректно!")
