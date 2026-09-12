import pytest
import httpx
from fastapi.testclient import TestClient
from gateway import app, settings
from unittest.mock import patch

client = TestClient(app)
VALID_HEADERS = {"X-API-Key": settings.GATEWAY_API_KEY}
INVALID_HEADERS = {"X-API-Key": "invalid_key"}

#Authentication Tests

def test_search_missing_api_key():
    response = client.get("/api/v1/search?q=Sony")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API Key"

def test_search_invalid_api_key():
    response = client.get("/api/v1/search?q=Sony", headers=INVALID_HEADERS)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API Key"

def test_search_authorized():
    response = client.get("/api/v1/search?q=Sony", headers=VALID_HEADERS)
    assert response.status_code == 200
    assert "results" in response.json()
    assert "limit" in response.json()

#Endpoint Functionality Tests

def test_search_with_category_filter():
    response = client.get("/api/v1/search?q=Light&categoryid=LGT", headers=VALID_HEADERS)
    assert response.status_code == 200
    assert response.json()["category_filter"] == "LGT"

def test_live_assets_endpoint():
    mock_payload = [
        {"id": "A-101", "item_id": "1001", "assetid": "SN-FX6-001", "assetstatus": "In"}
    ]
    mock_response = httpx.Response(status_code=200, json=mock_payload)

    with patch("gateway.httpx.AsyncClient.get", return_value=mock_response):
        response = client.get("/api/v1/items/1001/assets", headers=VALID_HEADERS)
        assert response.status_code == 200
        assert response.json()["item_id"] == "1001"
        assert response.json()["assets"][0]["assetid"] == "SN-FX6-001"