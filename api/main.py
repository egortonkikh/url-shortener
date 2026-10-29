import os
import string
import random
import psycopg2
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="URL Shortener API")

class UrlCreate(BaseModel):
    original_url: str

# Настройки подключения
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "shortener")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")

# Подключаем Redis
redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

def get_db():
    return psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME)

@app.on_event("startup")
def startup():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            short_code VARCHAR(10) UNIQUE NOT NULL,
            original_url TEXT NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Таблица urls создана!")

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.post("/shorten")
def shorten_url(url_data: UrlCreate):
    short_code = generate_short_code()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO urls (short_code, original_url) VALUES (%s, %s) RETURNING short_code",
        (short_code, url_data.original_url)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    # Сохраняем в Redis для быстрого доступа в будущем
    redis_client.set(short_code, url_data.original_url)
    
    return {"short_code": short_code, "original_url": url_data.original_url}

@app.get("/{short_code}")
def redirect_url(short_code: str):
    # Сначала проверяем Redis (быстро!)
    original_url = redis_client.get(short_code)
    
    if original_url:
        print(f"⚡ Найдено в Redis: {short_code}")
        return {"redirect_to": original_url, "source": "cache"}
    
    # Если в Redis нет — идем в PostgreSQL
    print(f"📚 Найдено в PostgreSQL: {short_code}")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT original_url FROM urls WHERE short_code = %s", (short_code,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        redis_client.set(short_code, result[0])
        return {"redirect_to": result[0], "source": "database"}
    
    raise HTTPException(status_code=404, detail="Ссылка не найдена")