from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

origins = [
    "https://www.aifetish.xyz",  # Разрешите ваш продакшен-домен
    "http://localhost:8000",  # Для локальной разработки (опционально)
    "http://127.0.0.1:5500",   # Для локальной разработки (опционально)
]

app.add_middleware(
    CORSMiddleware,
    #allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Расширенные промпты для жанров
GENRE_PROMPTS = {
    "comedy": {
        "name": "Комедия",
        "prompt": "Ты эксперт в комедийных фильмах...",
        "emoji": "😂"
    },
    "horror": {
        "name": "Ужасы", 
        "prompt": "Ты специалист по хоррор-фильмам...",
        "emoji": "👻"
    },
    "drama": {
        "name": "Драма",
        "prompt": "Ты знаток драматического кино...",
        "emoji": "🎭"
    },
    "sci_fi": {
        "name": "Научная фантастика",
        "prompt": "Ты эксперт по научной фантастике...",
        "emoji": "🚀"
    },
    "action": {
        "name": "Боевик",
        "prompt": "Ты специалист по боевикам...",
        "emoji": "💥"
    }
}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    enabled_genres: List[str]

class StartChatRequest(BaseModel):
    enabled_genres: List[str]

def create_system_prompt(enabled_genres: List[str]) -> str:
    """Создает объединенный системный промпт"""
    if not enabled_genres:
        return "Ты помощник по фильмам. Отвечай на вопросы о кино."
    
    base_prompt = "Ты кинопомощник со специализацией в следующих жанрах:\n\n"
    
    for genre in enabled_genres:
        if genre in GENRE_PROMPTS:
            base_prompt += f"• {GENRE_PROMPTS[genre]['prompt']}\n\n"
    
    base_prompt += "Сочетай стили выбранных жанров в своих ответах. "
    base_prompt += "Отвечай на вопросы пользователя в соответствии с выбранными жанровыми специализациями."
    
    return base_prompt

@app.post("/api/chat/start")
async def start_chat(request: StartChatRequest):
    """Инициализация чата с выбранными жанрами"""
    try:
        if not request.enabled_genres:
            raise HTTPException(status_code=400, detail="No genres selected")
        
        system_prompt = create_system_prompt(request.enabled_genres)
        
        return {
            "success": True,
            "system_prompt": system_prompt,
            "enabled_genres": request.enabled_genres,
            "message": f"Чат инициализирован с {len(request.enabled_genres)} жанрами"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Основной обработчик чата"""
    try:
        system_prompt = create_system_prompt(request.enabled_genres)
        
        messages_with_system = [
            {"role": "system", "content": system_prompt}
        ] + [msg.dict() for msg in request.messages]
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "HTTP-Referer": "https://aifetish.xyz",
                "X-Title": "Film AI Assistant",
                "Content-Type": "application/json"
            },
            json={
                "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                "messages": messages_with_system,
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, 
                              detail=f"OpenRouter API error: {response.text}")
        
        response_data = response.json()
        ai_response = response_data['choices'][0]['message']['content']
        
        return {"response": ai_response}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/genres")
async def get_genres_info():
    """Возвращает информацию о доступных жанрах"""
    return {
        "available_genres": {
            genre: {
                "name": info["name"],
                "emoji": info["emoji"],
                "description": info["prompt"][:100] + "..."
            }
            for genre, info in GENRE_PROMPTS.items()
        }
    }

@app.get("/api/health")
async def health_check():
    """Проверка работы API"""
    return {"status": "ok", "message": "API is working"}