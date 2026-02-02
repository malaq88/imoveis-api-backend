"""
Sistema de cache para consultas frequentes
"""
import logging
from functools import wraps
from typing import Callable, Any
from cachetools import TTLCache
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache em memória com TTL
cache = TTLCache(maxsize=1000, ttl=settings.CACHE_TTL_SECONDS) if settings.CACHE_ENABLED else None


def cached(key_prefix: str = ""):
    """
    Decorator para cachear resultados de funções
    
    Args:
        key_prefix: Prefixo para a chave do cache
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not settings.CACHE_ENABLED or cache is None:
                return await func(*args, **kwargs)
            
            # Gera chave do cache baseada nos argumentos
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            if cache_key in cache:
                logger.debug(f"Cache hit: {cache_key}")
                return cache[cache_key]
            
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            cache[cache_key] = result
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not settings.CACHE_ENABLED or cache is None:
                return func(*args, **kwargs)
            
            # Gera chave do cache baseada nos argumentos
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            if cache_key in cache:
                logger.debug(f"Cache hit: {cache_key}")
                return cache[cache_key]
            
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            cache[cache_key] = result
            return result
        
        # Retorna wrapper apropriado baseado se a função é async ou não
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def clear_cache(pattern: str = None):
    """
    Limpa o cache
    
    Args:
        pattern: Padrão para limpar apenas chaves que começam com o padrão
    """
    if cache is None:
        return
    
    if pattern:
        keys_to_remove = [key for key in cache.keys() if key.startswith(pattern)]
        for key in keys_to_remove:
            del cache[key]
        logger.info(f"Cache limpo: {len(keys_to_remove)} chaves removidas (padrão: {pattern})")
    else:
        cache.clear()
        logger.info("Cache completamente limpo")

