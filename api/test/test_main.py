import pytest
from fastapi.testclient import TestClient
from main import app

# Создаем тестовый клиент
client = TestClient(app)

def test_create_short_url():
    """Тест: создание короткой ссылки"""
    response = client.post(
        "/shorten",
        json={"original_url": "https://google.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://google.com"
    assert len(data["short_code"]) == 6

def test_redirect_existing_url():
    """Тест: редирект существующей ссылки"""
    # Сначала создаем ссылку
    create_response = client.post(
        "/shorten",
        json={"original_url": "https://youtube.com"}
    )
    short_code = create_response.json()["short_code"]
    
    # Теперь делаем редирект
    response = client.get(f"/{short_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["redirect_to"] == "https://youtube.com"
    assert data["source"] in ["database", "cache"]

def test_redirect_not_found():
    """Тест: несуществующая ссылка возвращает 404"""
    response = client.get("/nonexistent123")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data