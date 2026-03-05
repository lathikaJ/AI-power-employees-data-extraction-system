import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

import os
os.environ["OPENROUTER_API_KEY"] = "test-key"

from main import app

client = TestClient(app)

@pytest.fixture
def mock_openai_success():
    """Mocks a successful OpenAI API JSON response mapping to the Employee schema."""
    with patch("api.routes.extraction_service.ai_agent.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"employees": [{"name": "John Doe", "email": "john@example.com", "designation": "Software Engineer"}]}'
        mock_create.return_value = mock_response
        yield mock_create

@pytest.fixture
def mock_openai_malformed():
    """Mocks a malformed response from OpenAI missing the 'employees' structural key."""
    with patch("api.routes.extraction_service.ai_agent.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"not_employees": "bad formatting"}'
        mock_create.return_value = mock_response
        yield mock_create

@pytest.fixture
def mock_crawl_agent():
    """Mocks a successful extraction crawl yielding raw HTML content."""
    with patch("api.routes.extraction_service.crawl_agent.crawl", new_callable=AsyncMock) as mock_crawl:
        mock_crawl.return_value = ["<html><body>John Doe works here.</body></html>"]
        yield mock_crawl

@pytest.fixture
def mock_crawl_agent_empty():
    """Mocks an empty crawl execution yielding no pages."""
    with patch("api.routes.extraction_service.crawl_agent.crawl", new_callable=AsyncMock) as mock_crawl:
        mock_crawl.return_value = []
        yield mock_crawl

def test_invalid_url():
    """Test standard Pydantic schema validation failures for bad URLs."""
    response = client.post("/api/v1/extract", json={"url": "not-a-valid-url"})
    # Could be 400 from our InputAgent InvalidURLError or 422 depending on how pydantic rejects it initially
    assert response.status_code in [400, 422]

def test_blocked_internal_ip():
    """Test SSRF rejection block against local host IP resolutions."""
    with patch("socket.gethostbyname", return_value="127.0.0.1"):
        response = client.post("/api/v1/extract", json={"url": "http://localhost.corp"})
        assert response.status_code == 400
        error_detail = response.json()["detail"].lower()
        assert "ssrf" in error_detail or "restricted ip" in error_detail

def test_empty_html(mock_crawl_agent_empty):
    """Test orchestration when the Crawler component fails to locate pages yielding an empty array."""
    response = client.post("/api/v1/extract", json={"url": "https://example.com"})
    assert response.status_code == 200
    assert response.json()["total_count"] == 0
    assert response.json()["employees"] == []

def test_malformed_ai_response(mock_crawl_agent, mock_openai_malformed):
    """Test AI JSON Parsing failure and cleanup mechanics allowing graceful 0 count returns."""
    response = client.post("/api/v1/extract", json={"url": "https://example.com"})
    assert response.status_code == 200
    assert response.json()["total_count"] == 0
    assert response.json()["employees"] == []

def test_successful_extraction(mock_crawl_agent, mock_openai_success):
    """Test full integration success returning precisely cleansed data mapped correctly."""
    response = client.post("/api/v1/extract", json={"url": "https://example.com"})
    assert response.status_code == 200
    assert response.json()["total_count"] == 1
    assert response.json()["employees"][0]["name"] == "John Doe"
    assert response.json()["employees"][0]["email"] == "john@example.com"
