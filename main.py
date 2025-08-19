from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из .env

app = FastAPI()

# Настройка CORS (разрешаем запросы из браузера)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки. В продакшене укажите конкретный домен!
    allow_methods=["POST"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "https://aifetish.xyz/",  # Заuvicorn main:app --reloadмените на ваш URL
            "X-Title": "AI Chat",
            "Content-Type": "application/json"
        },
        json={
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "messages": data["messages"],
            "temperature": 0.7
        }
    )
    
    return response.json()