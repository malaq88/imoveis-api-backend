import logging
from contextlib import asynccontextmanager
from app.controllers import imovel_controller, user_controller, health_controller

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.dependencies import lifespan
from app.core.config import settings
from app.core.rate_limit import limiter, _rate_limit_exceeded_handler
from database import engine, Base

# Configuração de logging
# Determina o nível de log baseado no ambiente ou variável de ambiente
if settings.ENVIRONMENT == "production":
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
else:
    log_level = logging.DEBUG

# Configura handlers de logging
handlers = [logging.StreamHandler()]  # Sempre loga no console

# Adiciona handler de arquivo se LOG_FILE estiver configurado
if settings.LOG_FILE:
    try:
        handlers.append(logging.FileHandler(settings.LOG_FILE))
    except (OSError, IOError) as e:
        # Se não conseguir criar o arquivo de log, apenas loga no console
        print(f"AVISO: Não foi possível criar arquivo de log '{settings.LOG_FILE}': {e}")

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers
)
logger = logging.getLogger(__name__)

# Cria tabelas no banco
Base.metadata.create_all(bind=engine)

# Cria a aplicação FastAPI com lifespan
app = FastAPI(
    lifespan=lifespan,
    title="Imóveis API",
    description="""
    API RESTful para gerenciamento de imóveis de temporada.
    
    ## Funcionalidades
    
    * 🔐 Autenticação JWT
    * 👥 Gerenciamento de usuários
    * 🏠 CRUD completo de imóveis
    * 📸 Upload e gerenciamento de imagens
    * 📄 Paginação em todas as listagens
    * 🔍 Filtros avançados
    * 🚦 Rate limiting
    * 💾 Cache de consultas
    
    ## Autenticação
    
    Para usar a API, você precisa:
    1. Fazer login em `/token` com username e password
    2. Usar o token retornado no header: `Authorization: Bearer <token>`
    """,
    version="1.0.0",
    contact={
        "name": "Suporte API",
        "email": "suporte@imoveis.com",
    },
    license_info={
        "name": "MIT",
    },
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# --- Endpoints ---
app.include_router(health_controller.router)
app.include_router(user_controller.router)
app.include_router(imovel_controller.router)