import asyncio
import logging
import re
from typing import List, Dict, Any
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bs4 import BeautifulSoup
import aiohttp
import nest_asyncio

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "qwen3-embedding:4b"
LLM_MODEL = "qwen3:4b-instruct-2507-q4_K_M"

class SearchRequest(BaseModel):
    query: str
    page_html: str

class SearchResponse(BaseModel):
    users: List[Dict[str, Any]]
    answer: str

class SimpleSemanticSearch:
    def __init__(self):
        self.current_users = []
        self.current_embeddings = []
        
    def parse_users_from_html(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        users = []
        
        user_cards = soup.find_all('div', class_='user-card')
        logger.info(f"Найдено {len(user_cards)} карточек пользователей")
        
        for card in user_cards:
            try:
                name_tag = card.find('h3')
                if not name_tag:
                    continue
                    
                name_text = name_tag.text.strip()
                match = re.match(r'(.+?)\s*\((\d+)\s*лет\)', name_text)
                if not match:
                    continue
                    
                username = match.group(1)
                age = int(match.group(2))
                
                match_percent_tag = card.find('div', class_='match-percentage')
                match_percent = 0
                if match_percent_tag:
                    percent_text = match_percent_tag.text
                    percent_match = re.search(r'(\d+)%', percent_text)
                    if percent_match:
                        match_percent = int(percent_match.group(1))
                
                prefs = {}
                pref_texts = card.find_all('p')
                for p in pref_texts:
                    text = p.text
                    if '🍕 Еда:' in text:
                        prefs['food'] = text.replace('🍕 Еда:', '').strip()
                    elif '📚 Книги:' in text:
                        prefs['books'] = text.replace('📚 Книги:', '').strip()
                    elif '🎬 Фильмы:' in text:
                        prefs['movies'] = text.replace('🎬 Фильмы:', '').strip()
                
                user_data = {
                    'username': username,
                    'age': age,
                    'match_percentage': match_percent,
                    'food': prefs.get('food', 'не указано'),
                    'books': prefs.get('books', 'не указано'),
                    'movies': prefs.get('movies', 'не указано'),
                    'text': f"{username} {age} лет. Любит: {prefs.get('food', 'не указано')}. Книги: {prefs.get('books', 'не указано')}. Фильмы: {prefs.get('movies', 'не указано')}"
                }
                users.append(user_data)
                
            except Exception as e:
                logger.error(f"Ошибка парсинга: {e}")
                continue
        
        return users
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        
        for text in texts:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{OLLAMA_URL}/api/embeddings",
                        json={
                            "model": EMBEDDING_MODEL,
                            "prompt": text
                        },
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            embeddings.append(result.get('embedding', []))
                        else:
                            logger.error(f"Ошибка получения эмбеддинга: {response.status}")
                            embeddings.append([])
            except Exception as e:
                logger.error(f"Ошибка при получении эмбеддинга: {e}")
                embeddings.append([])
        
        return embeddings
    
    def cosine_similarity(self, vec1, vec2):
        if not vec1 or not vec2:
            return 0
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot_product / (norm1 * norm2)
    
    async def search_similar(self, query: str, users: List[Dict[str, Any]], top_k: int = 5):
        if not users:
            return []
        
        logger.info(f"Получаем эмбеддинг для запроса: {query[:50]}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "prompt": query
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    logger.error("Не удалось получить эмбеддинг запроса")
                    return []
                query_result = await response.json()
                query_embedding = query_result.get('embedding', [])
        
        if not query_embedding:
            logger.error("Пустой эмбеддинг запроса")
            return []
        
        user_texts = [user['text'] for user in users]
        
        logger.info(f"Получаем эмбеддинги для {len(user_texts)} пользователей...")
        
        user_embeddings = []
        for i, text in enumerate(user_texts):
            if i % 50 == 0:
                logger.info(f"Обработано {i}/{len(user_texts)} пользователей")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{OLLAMA_URL}/api/embeddings",
                        json={
                            "model": EMBEDDING_MODEL,
                            "prompt": text
                        },
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            user_embeddings.append(result.get('embedding', []))
                        else:
                            user_embeddings.append([])
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                user_embeddings.append([])
        
        similarities = []
        for i, emb in enumerate(user_embeddings):
            sim = self.cosine_similarity(query_embedding, emb)
            similarities.append((i, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for i, sim in similarities[:top_k]:
            if sim > 0.1:
                user = users[i].copy()
                user['similarity_score'] = round(sim, 3)
                results.append(user)
        
        return results
    
    async def generate_response(self, query: str, users: List[Dict[str, Any]]) -> str:
        if not users:
            return "К сожалению, не найдено подходящих пользователей по вашему запросу. Попробуйте переформулировать запрос."
        
        users_text = ""
        for i, user in enumerate(users[:3], 1):
            users_text += f"\n{i}. **{user['username']}** (возраст {user['age']} лет)\n"
            users_text += f"   Сходство: {int(user['similarity_score'] * 100)}%\n"
            users_text += f"   Интересы: {user['food']}\n"
            users_text += f"   Книги: {user['books']}\n"
            users_text += f"   Фильмы: {user['movies']}\n"
        
        prompt = f"""Ты дружелюбный помощник сайта знакомств. Пользователь ищет друзей по интересам.

Запрос: "{query}"

Подходящие пользователи:
{users_text}

Напиши короткий дружелюбный ответ на русском языке:
1. Кратко представь найденных пользователей
2. Объясни, почему они подходят
3. Посоветуй, с кем начать общение
4. Добавь позитивное пожелание

Ответ должен быть кратким и теплым."""
        
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
                            "max_tokens": 300
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('response', 'Извините, не удалось сгенерировать ответ')
                    else:
                        return "Извините, сервис ИИ временно недоступен."
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return "Извините, произошла ошибка при генерации ответа."

semantic_search = SimpleSemanticSearch()

def setup_semantic_routes(app: FastAPI):
    
    @app.post("/api/semantic/search")
    async def semantic_search_endpoint(request: SearchRequest):
        try:
            logger.info(f"Поиск по запросу: {request.query[:50]}...")
            
            users = semantic_search.parse_users_from_html(request.page_html)
            
            if not users:
                return SearchResponse(users=[], answer="Не найдено пользователей на странице")
            
            logger.info(f"Найдено {len(users)} пользователей, ищем похожих...")
            
            similar_users = await semantic_search.search_similar(request.query, users)
            
            logger.info(f"Найдено {len(similar_users)} похожих пользователей")
            
            answer = await semantic_search.generate_response(request.query, similar_users)
            
            return SearchResponse(users=similar_users, answer=answer)
            
        except asyncio.TimeoutError:
            logger.error("Таймаут")
            raise HTTPException(status_code=504, detail="Поиск занял слишком много времени")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/semantic/status")
    async def semantic_status():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{OLLAMA_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        models = await response.json()
                        models_list = [m['name'] for m in models.get('models', [])]
                        return {
                            "status": "ok",
                            "ollama_available": True,
                            "models": models_list,
                            "embedding_model": EMBEDDING_MODEL,
                            "llm_model": LLM_MODEL
                        }
                    else:
                        return {
                            "status": "error",
                            "ollama_available": False,
                            "message": "Ollama не отвечает"
                        }
        except Exception as e:
            return {
                "status": "error",
                "ollama_available": False,
                "message": str(e)
            }