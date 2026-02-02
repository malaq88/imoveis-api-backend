"""
Rate limiting para a API
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from app.core.config import settings
from functools import wraps

# Inicializa o limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"] if settings.RATE_LIMIT_ENABLED else []
)

def get_rate_limit_key(request: Request) -> str:
    """Gera chave para rate limiting baseada no IP e usuário autenticado"""
    # Tenta obter o usuário autenticado se houver
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)

# Wrapper para o método limit que verifica se rate limiting está habilitado
_original_limit = limiter.limit

def limit(*args, **kwargs):
    """Wrapper para limiter.limit que verifica se rate limiting está habilitado"""
    if not settings.RATE_LIMIT_ENABLED:
        # Se rate limiting está desabilitado, retorna um decorator que não faz nada
        def noop_decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return noop_decorator
    # Se rate limiting está habilitado, usa o comportamento original
    return _original_limit(*args, **kwargs)

# Substitui o método limit do limiter
limiter.limit = limit

