from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_optimizer_service
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_optimize_validation(client: TestClient) -> None:
    response = client.post("/api/v1/optimize", json={"prompt": ""})
    assert response.status_code == 422


def test_optimize_success(client: TestClient) -> None:
    mock_service = AsyncMock()
    mock_service.optimize.return_value = "Write a concise professional email."
    mock_service.model_name = "claude-test"

    app = client.app
    app.dependency_overrides[get_optimizer_service] = lambda: mock_service

    response = client.post(
        "/api/v1/optimize",
        json={
            "prompt": "I was wondering if you could maybe help me write a really good email please"
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["optimized_prompt"] == "Write a concise professional email."
    assert data["tokens_saved"] >= 0
    assert "cost_saved_usd" in data
