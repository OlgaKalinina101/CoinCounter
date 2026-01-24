"""
NLP утилиты для продвинутой обработки текста транзакций.
Включает лемматизацию, работу с синонимами и multi-query обработку.
"""

import re
import logging
from typing import List, Set, Dict, Tuple
from functools import lru_cache

try:
    import pymorphy2
    PYMORPHY_AVAILABLE = True
except ImportError:
    PYMORPHY_AVAILABLE = False
    
try:
    from ruwordnet import RuWordNet
    RUWORDNET_AVAILABLE = True
except ImportError:
    RUWORDNET_AVAILABLE = False

from coin_desk.utils.embedding import calculate_similarity

logger = logging.getLogger('coin_desk')


class NLPProcessor:
    """Обработчик текста с продвинутыми NLP возможностями"""
    
    def __init__(self):
        # Инициализация pymorphy2
        self.morph = pymorphy2.MorphAnalyzer() if PYMORPHY_AVAILABLE else None
        
        # Инициализация RuWordNet (с обработкой ошибок)
        self.wordnet = None
        if RUWORDNET_AVAILABLE:
            try:
                self.wordnet = RuWordNet()
            except Exception as e:
                logger.warning(f"Failed to load RuWordNet: {e}")
        
        if not PYMORPHY_AVAILABLE:
            logger.warning("pymorphy2 not installed, lemmatization unavailable")
        if not RUWORDNET_AVAILABLE:
            logger.warning("ruwordnet not installed, synonym expansion unavailable")
    
    @lru_cache(maxsize=1000)
    def lemmatize(self, word: str) -> str:
        """
        Лемматизация слова (приведение к начальной форме).
        
        Args:
            word: Слово для лемматизации
            
        Returns:
            Лемма (начальная форма слова)
        """
        if not self.morph or not word:
            return word.lower()
        
        try:
            parsed = self.morph.parse(word)[0]
            return parsed.normal_form
        except Exception as e:
            logger.debug(f"Lemmatization error for '{word}': {e}")
            return word.lower()
    
    @lru_cache(maxsize=500)
    def get_synonyms(self, word: str, limit: int = 10) -> Set[str]:
        """
        Получение синонимов слова из RuWordNet.
        
        Args:
            word: Слово для поиска синонимов
            limit: Максимальное количество синонимов
            
        Returns:
            Множество синонимов
        """
        if not self.wordnet:
            return {word}
        
        try:
            synonyms = set()
            synsets = self.wordnet.get_synsets(word)
            
            for synset in synsets[:3]:  # Берем первые 3 синсета
                for word_obj in synset.get_words():
                    synonyms.add(word_obj.lemma())
                    if len(synonyms) >= limit:
                        break
                if len(synonyms) >= limit:
                    break
            
            return synonyms if synonyms else {word}
        except Exception as e:
            logger.debug(f"Synonym search error for '{word}': {e}")
            return {word}
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Разбивает текст на предложения (multi-query).
        
        Args:
            text: Исходный текст
            
        Returns:
            Список предложений
        """
        if not text:
            return []
        
        # Простая разбивка по знакам препинания
        sentences = re.split(r'[.!?;,\n]+', text)
        # Фильтруем пустые и очень короткие (< 3 символов)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
        
        return sentences if sentences else [text]
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Извлекает ключевые слова из текста (существительные и глаголы).
        
        Args:
            text: Исходный текст
            
        Returns:
            Список ключевых слов в нормальной форме
        """
        if not self.morph:
            return text.lower().split()
        
        # Убираем специальные символы, оставляем только буквы и пробелы
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        keywords = []
        for word in words:
            if len(word) < 3:  # Пропускаем короткие слова
                continue
            
            try:
                parsed = self.morph.parse(word)[0]
                # Берем только существительные и глаголы
                if 'NOUN' in parsed.tag or 'VERB' in parsed.tag:
                    keywords.append(parsed.normal_form)
            except Exception:
                continue
        
        return keywords
    
    def expand_query_with_synonyms(self, text: str) -> Set[str]:
        """
        Расширяет запрос синонимами ключевых слов.
        
        Args:
            text: Исходный текст
            
        Returns:
            Множество расширенных терминов (оригинальные + синонимы)
        """
        keywords = self.extract_keywords(text)
        expanded = set(keywords)
        
        for keyword in keywords:
            synonyms = self.get_synonyms(keyword)
            expanded.update(synonyms)
        
        return expanded


class AdvancedCategoryMatcher:
    """
    Продвинутый алгоритм подбора категории для транзакции.
    Использует multi-query, лемматизацию, синонимы, vector search и бустинг.
    """
    
    def __init__(self):
        self.nlp = NLPProcessor()
    
    def calculate_match_score(
        self,
        transaction_text: str,
        category_keyword: str,
        base_similarity: float
    ) -> Tuple[float, Dict[str, bool]]:
        """
        Вычисляет итоговый скор совпадения с учётом бустинга.
        
        Args:
            transaction_text: Текст транзакции (назначение платежа)
            category_keyword: Ключевое слово категории
            base_similarity: Базовая схожесть от эмбеддингов (0..1)
            
        Returns:
            Кортеж (итоговый_скор, флаги_бустов)
        """
        boosts = {
            'exact_match': False,
            'lemma_match': False,
            'synonym_match': False
        }
        
        # Нормализуем тексты
        text_lower = transaction_text.lower()
        keyword_lower = category_keyword.lower()
        
        # 1. Exact match: точное совпадение слова (бонус +0.25)
        if keyword_lower in text_lower:
            boosts['exact_match'] = True
            base_similarity += 0.25
        
        # 2. Лемматизация: совпадение лемм (бонус +0.15)
        text_lemmas = {self.nlp.lemmatize(w) for w in text_lower.split() if len(w) > 2}
        keyword_lemma = self.nlp.lemmatize(keyword_lower)
        
        if keyword_lemma in text_lemmas:
            boosts['lemma_match'] = True
            base_similarity += 0.15
        
        # 3. Синонимы: совпадение через синонимы (бонус +0.10)
        keyword_synonyms = self.nlp.expand_query_with_synonyms(keyword_lower)
        if text_lemmas & keyword_synonyms:  # Пересечение множеств
            boosts['synonym_match'] = True
            base_similarity += 0.10
        
        # Ограничиваем максимальный скор 1.0
        final_score = min(base_similarity, 1.0)
        
        return final_score, boosts
    
    def find_best_category(
        self,
        transaction_text: str,
        category_keywords: Dict[str, List[str]],
        threshold: float = 0.7
    ) -> Tuple[str, float, Dict[str, bool]]:
        """
        Находит наилучшую категорию для транзакции.
        
        Args:
            transaction_text: Текст транзакции (назначение платежа)
            category_keywords: Словарь {категория: [ключевые_слова]}
            threshold: Минимальный порог совпадения
            
        Returns:
            Кортеж (название_категории, скор, примененные_бусты) или (None, 0, {})
        """
        # Multi-query: разбиваем на предложения
        sentences = self.nlp.split_into_sentences(transaction_text)
        
        best_category = None
        best_score = 0.0
        best_boosts = {}
        
        # Перебираем категории и их ключевые слова
        for category_name, keywords in category_keywords.items():
            for keyword in keywords:
                # Vector search: вычисляем эмбеддинг-схожесть для каждого предложения
                max_embedding_similarity = 0.0
                
                for sentence in sentences:
                    similarity = calculate_similarity(sentence, keyword)
                    max_embedding_similarity = max(max_embedding_similarity, similarity)
                
                # Применяем бустинг
                final_score, boosts = self.calculate_match_score(
                    transaction_text,
                    keyword,
                    max_embedding_similarity
                )
                
                # Обновляем лучший результат
                if final_score > best_score:
                    best_score = final_score
                    best_category = category_name
                    best_boosts = boosts
        
        # Возвращаем результат только если превышен порог
        if best_score >= threshold:
            return best_category, best_score, best_boosts
        
        return None, 0.0, {}


# Singleton экземпляры для переиспользования
_nlp_processor = None
_category_matcher = None


def get_nlp_processor() -> NLPProcessor:
    """Получить глобальный экземпляр NLPProcessor"""
    global _nlp_processor
    if _nlp_processor is None:
        _nlp_processor = NLPProcessor()
    return _nlp_processor


def get_category_matcher() -> AdvancedCategoryMatcher:
    """Получить глобальный экземпляр AdvancedCategoryMatcher"""
    global _category_matcher
    if _category_matcher is None:
        _category_matcher = AdvancedCategoryMatcher()
    return _category_matcher
