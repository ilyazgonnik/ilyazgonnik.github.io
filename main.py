from contextlib import asynccontextmanager
import random
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import requests
import os
from dotenv import load_dotenv
from pathlib import Path 
import sqlite3
import json
from datetime import datetime, timedelta
load_dotenv()


# ✅ Оптимальный путь для Render.com
DB_PATH = os.path.join(os.getenv('HOME', ''), 'data', 'chats.db')

# Создаем директорию если нет
Path(os.path.dirname(DB_PATH)).mkdir(exist_ok=True)

# Инициализация базы данных
def init_db():
     """Инициализация базы с оптимизациями для малой памяти"""
     conn = sqlite3.connect(DB_PATH)
     c = conn.cursor()
    
     # Включаем оптимизации для малой памяти
     c.execute("PRAGMA journal_mode = WAL")  # Лучшая производительность
     c.execute("PRAGMA synchronous = NORMAL")  # Баланс скорость/надежность
     c.execute("PRAGMA cache_size = -2000")  # Кеш 2MB вместо дефолтных 2GB
    
     c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (session_id TEXT PRIMARY KEY,
                  selected_genres TEXT,
                  messages TEXT,
                  created_at TEXT,
                  last_activity TEXT)''')
    
     # Индекс для быстрого поиска
     c.execute('''CREATE INDEX IF NOT EXISTS idx_last_activity 
                 ON sessions(last_activity)''')
    
     conn.commit()
     conn.close()

# Сохранение сессии
def save_session(session_id, data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO sessions 
                 VALUES (?, ?, ?, ?, ?)''',
              (session_id,
               json.dumps(data['selected_genres']),
               json.dumps(data['messages']),
               data['created_at'],
               data['last_activity']))
    conn.commit()
    conn.close()

# Загрузка сессии
def load_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'selected_genres': json.loads(row[1]),
            'messages': json.loads(row[2]),
            'created_at': row[3],
            'last_activity': row[4]
        }
    return None

# Удаление сессии
def delete_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    #print("Database initialized")
    yield
    # Shutdown
    # Закрыть соединения если нужно

app = FastAPI(lifespan=lifespan)


origins = [
    "https://ilyazgonnik.github.io",  # URL вашего GitHub Pages сайта
    "http://localhost:8000",  # Для локальной разработки, можно удалить в продакшене
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
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
    selected_genres: List[str]
    session_id: Optional[str] = None


class StartChatRequest(BaseModel):
    selected_genres: List[str]

def create_system_prompt(selected_genres: List[str]) -> str:
    """Создает объединенный системный промпт"""
    if not selected_genres:
        return "Ты помощник по фильмам. Отвечай на вопросы о кино."
    
    base_prompt = "Ты кинопомощник со специализацией в следующих жанрах:\n\n"
    
    for genre in selected_genres:
        if genre in GENRE_PROMPTS:
            base_prompt += f"• {GENRE_PROMPTS[genre]['prompt']}\n\n"
    
    base_prompt += "Сочетай стили выбранных жанров в своих ответах. "
    base_prompt += "Отвечай на вопросы пользователя в соответствии с выбранными жанровыми специализациями."
    
    return base_prompt

@app.post("/api/chat/start")
async def start_chat(request: StartChatRequest):
    """Инициализация чата с выбранными жанрами"""
    try:
        if not request.selected_genres:
            raise HTTPException(status_code=400, detail="No genres selected")
        
        system_prompt = create_system_prompt(request.selected_genres)
        
        return {
            "success": True,
            "system_prompt": system_prompt,
            "selected_genres": request.selected_genres,
            "message": f"Чат инициализирован с {len(request.selected_genres)} жанрами"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def cleanup_old_sessions(days=7):
    """Очистка старых сессий для экономии места"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    c.execute('DELETE FROM sessions WHERE last_activity < ?', (cutoff_date,))
    
    deleted_count = c.rowcount
    conn.commit()
    conn.close()
    
    # Оптимизируем базу после удаления
    if deleted_count > 0:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("VACUUM")  # Освобождает место на диске
        conn.close()
    
    return deleted_count


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Основной обработчик чата"""
    try:
        system_prompt = create_system_prompt(request.selected_genres)
        
        session_id = request.session_id or str(uuid.uuid4())
        session_data = load_session(session_id)
        if not session_data:
            session_data = {
                'selected_genres': request.selected_genres,
                'messages': [],
                'created_at': datetime.utcnow().isoformat(),
                'last_activity': datetime.utcnow().isoformat()
            }
        
        messages_with_system = [
            {"role": "system", "content": system_prompt}
        ] + [msg.dict() for msg in request.messages] + session_data['messages']
        
        if len(session_data['messages']) > 40:
            session_data['messages'] = session_data['messages'][-20:]
        
        # ... обработка запроса ...
        
        # ✅ Сохраняем и сразу закрываем соединение
        save_session(session_id, session_data)
        
        # ✅ Периодическая очистка старых сессий
        if random.random() < 0.1:  # 10% chance to cleanup
            cleanup_old_sessions(days=3)
        
        response = requests.post(
            "https://api.venice.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('VENICE_API_KEY')}",
                "HTTP-Referer": "https://aifetish.xyz",
                "X-Title": "Film AI Assistant",
                "Content-Type": "application/json"
            },
            json={
                "model": "venice-uncensored",
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
        
        return {"response": ai_response, "session_id": session_id}
        
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


@app.get("/debug/db")
async def debug_db():
    """Проверка состояния базы данных"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Проверяем какие таблицы существуют
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        
        # Проверяем структуру таблицы sessions если она есть
        sessions_exists = any('sessions' in table for table in tables)
        sessions_structure = None
        
        if sessions_exists:
            c.execute("PRAGMA table_info(sessions)")
            sessions_structure = c.fetchall()
        
        conn.close()
        
        return {
            "db_path": DB_PATH,
            "tables": tables,
            "sessions_exists": sessions_exists,
            "sessions_structure": sessions_structure
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/health")
async def health_check():
    """Проверка работы API"""
    return {"status": "ok", "message": "API is working"}