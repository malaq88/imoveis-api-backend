"""
Configuração global para testes

Este arquivo é carregado automaticamente pelo pytest antes de qualquer teste.
Ele configura as variáveis de ambiente necessárias para os testes.
"""
import os
import pytest

# Configurações padrão para testes - definidas ANTES de qualquer import
TEST_ENV_VARS = {
    "SECRET_KEY": "test_secret_key_for_testing_only",
    "DATABASE_URL": "sqlite:///:memory:",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "ADMIN_USERNAME": "admin",
    "ADMIN_EMAIL": "admin@test.com",
    "ADMIN_PASSWORD": "admin123",
    "ENVIRONMENT": "testing",
    "CORS_ORIGINS": "*",
    "IMAGES_DIR": "/tmp/test_images",
    "MAX_FILE_SIZE_MB": "10",
    "DEFAULT_PAGE_SIZE": "10",
    "MAX_PAGE_SIZE": "100",
    "RATE_LIMIT_ENABLED": "false",
    "RATE_LIMIT_PER_MINUTE": "60",
    "CACHE_ENABLED": "false",
    "CACHE_TTL_SECONDS": "300",
}

# Configura variáveis de ambiente imediatamente quando o módulo é importado
# Isso garante que estejam disponíveis antes de qualquer import que use Settings
for key, value in TEST_ENV_VARS.items():
    if key not in os.environ:
        os.environ[key] = value

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configura o ambiente de testes antes de tudo"""
    # Garante que todas as variáveis estejam definidas
    for key, value in TEST_ENV_VARS.items():
        os.environ[key] = value
    
    yield
    
    # Limpa variáveis de ambiente após os testes (opcional)
    # Não limpamos para evitar problemas com imports subsequentes

