"""Smoke test - garante que Django sobe e health check responde."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_endpoint_returns_200():
    client = Client()
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "prontuario-ed"}
