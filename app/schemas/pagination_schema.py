from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Parâmetros de paginação"""
    page: int = Field(1, ge=1, description="Número da página")
    page_size: int = Field(10, ge=1, le=100, description="Itens por página")

class PaginatedResponse(BaseModel, Generic[T]):
    """Resposta paginada genérica"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        """Cria uma resposta paginada"""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

