"""
Health check e métricas da API
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.dependencies import get_db
from app.core.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["Health Check"],
)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Verifica o status da API e conectividade com o banco de dados"
)
def health_check(db: Session = Depends(get_db)):
    """
    Health check básico da API
    
    Retorna:
    - Status da API
    - Status da conexão com banco de dados
    - Informações do ambiente
    """
    try:
        # Testa conexão com banco de dados
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Erro ao conectar com banco de dados: {e}")
        db_status = "unhealthy"
    
    cache_status = "enabled" if settings.CACHE_ENABLED and cache else "disabled"
    cache_size = len(cache) if cache else 0
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status
        },
        "cache": {
            "status": cache_status,
            "size": cache_size,
            "max_size": cache.maxsize if cache else 0,
            "ttl_seconds": settings.CACHE_TTL_SECONDS
        },
        "rate_limiting": {
            "enabled": settings.RATE_LIMIT_ENABLED,
            "limit_per_minute": settings.RATE_LIMIT_PER_MINUTE
        }
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Verifica se a API está pronta para receber requisições"
)
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - verifica se todos os serviços estão prontos
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"API não está pronta: {e}")
        return {
            "status": "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }, status.HTTP_503_SERVICE_UNAVAILABLE


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Check",
    description="Verifica se a API está viva (usado por orquestradores como Kubernetes)"
)
def liveness_check():
    """
    Liveness check - verifica se a aplicação está rodando
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

