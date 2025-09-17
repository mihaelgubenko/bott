"""
Модуль для анализа эмоций и настроений пользователей
Использует VADER Sentiment и TextBlob для русского языка
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class SentimentResult:
    """Результат анализа настроения"""
    overall_sentiment: str  # positive, negative, neutral
    confidence: float  # 0.0 - 1.0
    emotions: Dict[str, float]  # specific emotions with scores
    psychological_indicators: Dict[str, float]  # stress, anxiety, etc.
    recommendation: str  # how to respond

class RussianSentimentAnalyzer:
    """Анализатор настроений для русского языка"""
    
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        
        # Словари для русского языка
        self.positive_words = {
            'хорошо', 'отлично', 'прекрасно', 'замечательно', 'радость', 'счастье',
            'любовь', 'успех', 'победа', 'достижение', 'мечта', 'надежда',
            'вдохновение', 'мотивация', 'энергия', 'позитив', 'улыбка', 'смех'
        }
        
        self.negative_words = {
            'плохо', 'ужасно', 'грустно', 'печально', 'депрессия', 'тревога',
            'страх', 'боль', 'одиночество', 'усталость', 'стресс', 'проблема',
            'трудность', 'неудача', 'разочарование', 'злость', 'гнев', 'ненависть'
        }
        
        self.stress_indicators = {
            'стресс', 'нервы', 'давление', 'напряжение', 'беспокойство',
            'волнение', 'паника', 'тревожность', 'переживания', 'нагрузка'
        }
        
        self.depression_indicators = {
            'депрессия', 'грусть', 'печаль', 'уныние', 'безнадежность',
            'пустота', 'апатия', 'безразличие', 'усталость', 'бессилие'
        }
        
        self.anxiety_indicators = {
            'тревога', 'беспокойство', 'волнение', 'страх', 'паника',
            'нервозность', 'неуверенность', 'сомнения', 'опасения'
        }

    def analyze_text(self, text: str) -> SentimentResult:
        """Основной метод анализа текста"""
        if not text or not text.strip():
            return SentimentResult(
                overall_sentiment='neutral',
                confidence=0.0,
                emotions={},
                psychological_indicators={},
                recommendation='neutral'
            )
        
        text_lower = text.lower()
        
        # Базовый анализ настроения
        sentiment_scores = self._analyze_sentiment(text_lower)
        
        # Анализ эмоций
        emotions = self._analyze_emotions(text_lower)
        
        # Психологические индикаторы
        psychological_indicators = self._analyze_psychological_state(text_lower)
        
        # Определение общего настроения
        overall_sentiment = self._determine_overall_sentiment(sentiment_scores)
        
        # Уверенность в оценке
        confidence = self._calculate_confidence(sentiment_scores, emotions)
        
        # Рекомендация по ответу
        recommendation = self._get_response_recommendation(
            overall_sentiment, emotions, psychological_indicators
        )
        
        return SentimentResult(
            overall_sentiment=overall_sentiment,
            confidence=confidence,
            emotions=emotions,
            psychological_indicators=psychological_indicators,
            recommendation=recommendation
        )

    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Анализ базового настроения"""
        # VADER анализ (работает с транслитерацией)
        vader_scores = self.vader.polarity_scores(text)
        
        # Подсчет положительных и отрицательных слов
        positive_count = sum(1 for word in self.positive_words if word in text)
        negative_count = sum(1 for word in self.negative_words if word in text)
        
        # Нормализация
        total_words = len(text.split())
        if total_words > 0:
            positive_ratio = positive_count / total_words
            negative_ratio = negative_count / total_words
        else:
            positive_ratio = negative_ratio = 0
        
        return {
            'vader_positive': vader_scores['pos'],
            'vader_negative': vader_scores['neg'],
            'vader_neutral': vader_scores['neu'],
            'vader_compound': vader_scores['compound'],
            'russian_positive': positive_ratio,
            'russian_negative': negative_ratio
        }

    def _analyze_emotions(self, text: str) -> Dict[str, float]:
        """Анализ конкретных эмоций"""
        emotions = {
            'joy': 0.0,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0,
            'surprise': 0.0,
            'disgust': 0.0
        }
        
        # Радость
        joy_words = {'радость', 'счастье', 'веселье', 'восторг', 'эйфория', 'блаженство'}
        emotions['joy'] = sum(1 for word in joy_words if word in text) / len(text.split())
        
        # Грусть
        sadness_words = {'грусть', 'печаль', 'тоска', 'уныние', 'меланхолия'}
        emotions['sadness'] = sum(1 for word in sadness_words if word in text) / len(text.split())
        
        # Злость
        anger_words = {'злость', 'гнев', 'ярость', 'бешенство', 'раздражение'}
        emotions['anger'] = sum(1 for word in anger_words if word in text) / len(text.split())
        
        # Страх
        fear_words = {'страх', 'ужас', 'паника', 'боязнь', 'фобия'}
        emotions['fear'] = sum(1 for word in fear_words if word in text) / len(text.split())
        
        return emotions

    def _analyze_psychological_state(self, text: str) -> Dict[str, float]:
        """Анализ психологического состояния"""
        indicators = {
            'stress_level': 0.0,
            'depression_risk': 0.0,
            'anxiety_level': 0.0,
            'emotional_stability': 0.5,
            'need_support': 0.0
        }
        
        total_words = len(text.split())
        if total_words == 0:
            return indicators
        
        # Уровень стресса
        stress_count = sum(1 for word in self.stress_indicators if word in text)
        indicators['stress_level'] = min(stress_count / total_words * 10, 1.0)
        
        # Риск депрессии
        depression_count = sum(1 for word in self.depression_indicators if word in text)
        indicators['depression_risk'] = min(depression_count / total_words * 10, 1.0)
        
        # Уровень тревожности
        anxiety_count = sum(1 for word in self.anxiety_indicators if word in text)
        indicators['anxiety_level'] = min(anxiety_count / total_words * 10, 1.0)
        
        # Потребность в поддержке
        support_words = {'помощь', 'поддержка', 'помоги', 'трудно', 'сложно', 'не справляюсь'}
        support_count = sum(1 for word in support_words if word in text)
        indicators['need_support'] = min(support_count / total_words * 10, 1.0)
        
        # Эмоциональная стабильность (обратная к общему негативу)
        total_negative = indicators['stress_level'] + indicators['depression_risk'] + indicators['anxiety_level']
        indicators['emotional_stability'] = max(0.1, 1.0 - total_negative / 3)
        
        return indicators

    def _determine_overall_sentiment(self, scores: Dict[str, float]) -> str:
        """Определение общего настроения"""
        # Комбинируем VADER и русский анализ
        compound_score = scores['vader_compound']
        russian_balance = scores['russian_positive'] - scores['russian_negative']
        
        final_score = (compound_score + russian_balance) / 2
        
        if final_score >= 0.1:
            return 'positive'
        elif final_score <= -0.1:
            return 'negative'
        else:
            return 'neutral'

    def _calculate_confidence(self, scores: Dict[str, float], emotions: Dict[str, float]) -> float:
        """Расчет уверенности в оценке"""
        # Чем больше эмоциональных индикаторов, тем выше уверенность
        emotion_strength = sum(emotions.values())
        vader_strength = abs(scores['vader_compound'])
        russian_strength = abs(scores['russian_positive'] - scores['russian_negative'])
        
        confidence = min((emotion_strength + vader_strength + russian_strength) / 3, 1.0)
        return max(confidence, 0.1)  # Минимальная уверенность

    def _get_response_recommendation(
        self, 
        sentiment: str, 
        emotions: Dict[str, float], 
        psychological: Dict[str, float]
    ) -> str:
        """Рекомендация по типу ответа"""
        
        # Высокая потребность в поддержке
        if psychological['need_support'] > 0.3:
            return 'supportive'
        
        # Высокий уровень стресса или тревоги
        if psychological['stress_level'] > 0.4 or psychological['anxiety_level'] > 0.4:
            return 'calming'
        
        # Риск депрессии
        if psychological['depression_risk'] > 0.3:
            return 'empathetic'
        
        # Положительные эмоции
        if sentiment == 'positive' and emotions['joy'] > 0.2:
            return 'encouraging'
        
        # Негативные эмоции
        if sentiment == 'negative':
            if emotions['anger'] > 0.2:
                return 'understanding'
            elif emotions['sadness'] > 0.2:
                return 'comforting'
            else:
                return 'supportive'
        
        # По умолчанию
        return 'balanced'

def get_sentiment_analyzer() -> RussianSentimentAnalyzer:
    """Фабричная функция для получения анализатора"""
    return RussianSentimentAnalyzer()

# Пример использования
if __name__ == "__main__":
    analyzer = get_sentiment_analyzer()
    
    test_texts = [
        "Я очень счастлив сегодня!",
        "Мне грустно и одиноко...",
        "У меня сильный стресс на работе",
        "Не знаю, что делать с этой проблемой"
    ]
    
    for text in test_texts:
        result = analyzer.analyze_text(text)
        print(f"\nТекст: {text}")
        print(f"Настроение: {result.overall_sentiment} ({result.confidence:.2f})")
        print(f"Рекомендация: {result.recommendation}")
        print(f"Психологические показатели: {result.psychological_indicators}")