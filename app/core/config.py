from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_USERNAME: str
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    IMAGES_DIR: str = "app/controllers/images"
    MAX_FILE_SIZE_MB: int = 10
    # CORS: lista separada por vírgulas ou "*" para permitir todos
    CORS_ORIGINS: str = "*"
    # Ambiente: "development" ou "production"
    ENVIRONMENT: str = "development"
    # Paginação
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    # Cache
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 300  # 5 minutos
    # Logging
    LOG_FILE: str = "app.log"
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Retorna lista de origens permitidas para CORS"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

# Cria settings - lê de variáveis de ambiente ou .env
# O conftest.py configura as variáveis de ambiente antes dos imports
settings = Settings()
