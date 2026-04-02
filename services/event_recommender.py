# services/event_recommender.py
"""
Модуль для автоматической генерации рекомендаций событий с использованием ИИ
"""

import asyncio
import logging
from typing import List, Dict, Any, Set
from datetime import datetime
from sqlmodel import Session, select
import aiohttp
import numpy as np

from database.connection import engine
from models.users import User
from models.events import Event
from models.ai_models import EventRecommendation

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация Ollama
OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "qwen3-embedding:4b"
LLM_MODEL = "qwen3:4b-instruct-2507-q4_K_M"

# Настройки рекомендаций
SIMILARITY_THRESHOLD = 0.80  # Минимальный порог сходства (0-1)
MAX_RECOMMENDATIONS_PER_USER = 3 # Максимум активных рекомендаций на пользователя
BATCH_SIZE = 20  # Количество пользователей в одной пачке


class EventRecommender:
    """Класс для генерации рекомендаций событий"""
    
    def __init__(self):
        self.similarity_threshold = SIMILARITY_THRESHOLD
        self.batch_size = BATCH_SIZE
    
    def _build_event_text(self, event: Event) -> str:
        """Формирует текст события для анализа"""
        tags_text = ', '.join(event.tags) if event.tags else 'нет'
        return f"""Название: {event.title}
Описание: {event.description}
Место проведения: {event.location}
Теги: {tags_text}"""
    
    def _build_user_text(self, user: User) -> str:
        """Формирует текст пользователя для анализа"""
        prefs = user.preferences
        food = ', '.join(prefs.get('food', [])) if prefs.get('food') else 'не указано'
        books = ', '.join(prefs.get('books', [])) if prefs.get('books') else 'не указано'
        movies = ', '.join(prefs.get('movies', [])) if prefs.get('movies') else 'не указано'
        
        return f"""Возраст: {user.age}
Любимая еда: {food}
Любимые книги: {books}
Любимые фильмы: {movies}"""
    
    async def _get_embedding(self, text: str, max_retries: int = 3) -> List[float]:
        """Получает эмбеддинг текста через Ollama с повторными попытками"""
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{OLLAMA_URL}/api/embeddings",
                        json={"model": EMBEDDING_MODEL, "prompt": text},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            embedding = result.get('embedding', [])
                            if embedding:
                                return embedding
                            else:
                                logger.warning(f"Пустой эмбеддинг, попытка {attempt + 1}")
                        else:
                            logger.warning(f"Ошибка {response.status}, попытка {attempt + 1}")
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут, попытка {attempt + 1}")
            except Exception as e:
                logger.warning(f"Ошибка: {e}, попытка {attempt + 1}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
        
        logger.error(f"Не удалось получить эмбеддинг после {max_retries} попыток")
        return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Вычисляет косинусное сходство между двумя векторами"""
        if not vec1 or not vec2:
            return 0.0
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot / (norm1 * norm2))
    
    def _find_common_interests(self, event: Event, user: User) -> List[str]:
        """Находит общие интересы между событием и пользователем"""
        event_tags = set(event.tags if event.tags else [])
        common = []
        
        for category in ['food', 'books', 'movies']:
            user_prefs = set(user.preferences.get(category, []))
            common.extend(event_tags.intersection(user_prefs))
        
        return common
    
    async def _generate_explanation(self, event: Event, user: User, similarity: float) -> str:
        """Генерирует персонализированное объяснение рекомендации"""
        common_interests = self._find_common_interests(event, user)
        
        if not common_interests:
            # Если нет общих тегов, используем общий текст
            return f"🎉 Это событие может вам понравиться! Совпадение интересов составляет {int(similarity * 100)}%."
        
        prompt = f"""Ты дружелюбный помощник сайта знакомств. Напиши короткое, теплое объяснение (1-2 предложения), почему пользователю стоит посетить это событие.

Событие: "{event.title}"
Описание: {event.description[:200]}
Теги события: {', '.join(event.tags[:5]) if event.tags else 'нет'}

Пользователь интересуется: {', '.join(common_interests[:3])}

Ответ должен быть:
- На русском языке
- Коротким (не более 30 слов)
- Позитивным и вдохновляющим
- Упоминать общие интересы

Твой ответ:"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": LLM_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "max_tokens": 100
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        explanation = result.get('response', '').strip()
                        if explanation and len(explanation) > 10:
                            return explanation
        except Exception as e:
            logger.error(f"Ошибка генерации объяснения: {e}")
        
        # Fallback объяснение
        interests_text = ', '.join(common_interests[:3])
        return f"🌟 Вы интересуетесь {interests_text}! Это событие создано специально для вас. Совпадение: {int(similarity * 100)}%."
    
    def _cleanup_old_recommendations(self, session: Session, user_id: int):
        """Удаляет старые рекомендации, если превышен лимит"""
        active_recs = session.exec(
            select(EventRecommendation).where(
                EventRecommendation.user_id == user_id,
                EventRecommendation.is_active == True
            )
        ).all()
        
        if len(active_recs) >= MAX_RECOMMENDATIONS_PER_USER:
            # Сортируем по дате (старые первые)
            active_recs.sort(key=lambda x: x.created_at)
            to_delete = active_recs[:len(active_recs) - MAX_RECOMMENDATIONS_PER_USER + 1]
            for rec in to_delete:
                rec.is_active = False
                session.add(rec)
                logger.info(f"Деактивирована старая рекомендация {rec.id} для пользователя {user_id}")
    
    async def recommend_for_all_users(self, event_id: int):
        """
        Главная функция: генерирует рекомендации для всех пользователей
        Вызывается после создания события
        """
        logger.info(f"🚀 Начинаем генерацию рекомендаций для события {event_id}")
        start_time = datetime.now()
        
        with Session(engine) as session:
            # 1. Получаем событие
            event = session.get(Event, event_id)
            if not event:
                logger.error(f"❌ Событие {event_id} не найдено")
                return
            
            logger.info(f"📌 Событие: {event.title}")
            
            # 2. Получаем эмбеддинг события
            event_text = self._build_event_text(event)
            logger.info("🔮 Получаем эмбеддинг события...")
            event_embedding = await self._get_embedding(event_text)
            
            if not event_embedding:
                logger.error("❌ Не удалось получить эмбеддинг события. Рекомендации не созданы.")
                return
            
            logger.info("✅ Эмбеддинг события получен")
            
            # 3. Получаем всех пользователей (кроме администратора)
            users = session.exec(
                select(User).where(User.is_admin == False)
            ).all()
            
            logger.info(f"👥 Всего пользователей: {len(users)}")
            
            if not users:
                logger.warning("Нет пользователей для рекомендаций")
                return
            
            # 4. Обрабатываем пользователей пачками
            recommendations_created = 0
            total_processed = 0
            
            for i in range(0, len(users), self.batch_size):
                batch = users[i:i + self.batch_size]
                logger.info(f"📦 Обрабатываем пачку {i//self.batch_size + 1}/{(len(users)-1)//self.batch_size + 1}")
                
                for user in batch:
                    total_processed += 1
                    
                    try:
                        # Получаем эмбеддинг пользователя
                        user_text = self._build_user_text(user)
                        user_embedding = await self._get_embedding(user_text)
                        
                        if not user_embedding:
                            continue
                        
                        # Вычисляем сходство
                        similarity = self._cosine_similarity(event_embedding, user_embedding)
                        
                        # Если сходство выше порога
                        if similarity >= self.similarity_threshold:
                            # Проверяем, нет ли уже активной рекомендации
                            existing = session.exec(
                                select(EventRecommendation).where(
                                    EventRecommendation.user_id == user.id,
                                    EventRecommendation.event_id == event_id,
                                    EventRecommendation.is_active == True
                                )
                            ).first()
                            
                            if existing:
                                continue
                            
                            # Генерируем объяснение
                            explanation = await self._generate_explanation(event, user, similarity)
                            
                            # Создаем рекомендацию
                            recommendation = EventRecommendation(
                                user_id=user.id,
                                event_id=event_id,
                                explanation=explanation,
                                is_active=True
                            )
                            session.add(recommendation)
                            recommendations_created += 1
                            
                            # Очищаем старые рекомендации если нужно
                            self._cleanup_old_recommendations(session, user.id)
                            
                            # Логируем создание
                            if recommendations_created % 10 == 0:
                                logger.info(f"✨ Создано {recommendations_created} рекомендаций")
                                
                    except Exception as e:
                        logger.error(f"Ошибка при обработке пользователя {user.id}: {e}")
                        continue
                
                # Коммитим после каждой пачки
                session.commit()
                logger.info(f"💾 Сохранено {recommendations_created} рекомендаций, обработано {total_processed}/{len(users)}")
            
            # 5. Итоги
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("=" * 50)
            logger.info(f"✅ Генерация рекомендаций завершена!")
            logger.info(f"📊 Итоги:")
            logger.info(f"   - Событие: {event.title} (ID: {event_id})")
            logger.info(f"   - Обработано пользователей: {total_processed}")
            logger.info(f"   - Создано рекомендаций: {recommendations_created}")
            logger.info(f"   - Время выполнения: {duration:.2f} сек")
            logger.info("=" * 50)


# Функция-обертка для вызова из фоновой задачи
async def recommend_event_for_users(event_id: int):
    """Асинхронная функция для запуска рекомендаций"""
    recommender = EventRecommender()
    await recommender.recommend_for_all_users(event_id)


# Синхронная обертка для BackgroundTasks (если нужно)
def recommend_event_sync(event_id: int):
    """Синхронная обертка для вызова из BackgroundTasks"""
    asyncio.run(recommend_event_for_users(event_id))