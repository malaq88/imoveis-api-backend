"""
Testes para rate limiting
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture(scope="function")
def client():
    """Cria um cliente de teste"""
    with TestClient(app) as test_client:
        yield test_client


class TestRateLimiting:
    """Testes para rate limiting"""
    
    def test_rate_limit_config(self):
        """Testa se rate limiting está configurado"""
        # Rate limiting pode estar desabilitado em testes
        assert hasattr(settings, 'RATE_LIMIT_ENABLED')
        assert hasattr(settings, 'RATE_LIMIT_PER_MINUTE')
    
    def test_health_endpoint_no_rate_limit(self, client):
        """Health endpoints não devem ter rate limiting"""
        # Health check deve sempre funcionar
        response = client.get("/health/")
        assert response.status_code == 200
        
        response = client.get("/health/live")
        assert response.status_code == 200
        
        response = client.get("/health/ready")
        assert response.status_code == 200

