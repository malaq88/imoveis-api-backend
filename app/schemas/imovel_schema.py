from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import List, Optional
from fastapi import Form

class ImageOut(BaseModel):
    id: int
    filename: str

    model_config = ConfigDict(from_attributes=True)

class ImovelBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(..., min_length=1)
    metragem: int = Field(..., gt=0, description="Metragem deve ser maior que zero")
    quartos: int = Field(..., ge=0, description="Número de quartos deve ser maior ou igual a zero")
    distancia_praia: str = Field(..., min_length=1)
    tipo_aluguel: str = Field(..., min_length=1)
    mobilhada: bool

class ImovelCreate(ImovelBase):
    preco: str
    disponivel: bool = True

    @classmethod
    def as_form(
        cls,
        titulo: str           = Form(...),
        descricao: str        = Form(...),
        metragem: int         = Form(...),
        quartos: int          = Form(...),
        distancia_praia: str  = Form(...),
        tipo_aluguel: str     = Form(...),
        mobilhada: bool       = Form(...),
        preco: str            = Form(...),
        disponivel: bool      = Form(True),
    ) -> "ImovelCreate":
        return cls(
            titulo=titulo,
            descricao=descricao,
            metragem=metragem,
            quartos=quartos,
            distancia_praia=distancia_praia,
            tipo_aluguel=tipo_aluguel,
            mobilhada=mobilhada,
            preco=preco,
            disponivel=disponivel,
        )

class ImovelUpdate(BaseModel):
    titulo:           Optional[str]      = None
    descricao:        Optional[str]      = None
    metragem:         Optional[int]      = None
    quartos:          Optional[int]      = None
    distancia_praia:  Optional[str]      = None
    tipo_aluguel:     Optional[str]      = None
    mobilhada:        Optional[bool]     = None
    preco:            Optional[str]      = None
    disponivel:       Optional[bool]     = None,
    image_filenames:  Optional[List[str]]= None

    @classmethod
    def as_form(
        cls,
        titulo: Optional[str]           = Form(None),
        descricao: Optional[str]        = Form(None),
        metragem: Optional[int]         = Form(None),
        quartos: Optional[int]          = Form(None),
        distancia_praia: Optional[str]  = Form(None),
        tipo_aluguel: Optional[str]     = Form(None),
        mobilhada: Optional[bool]       = Form(None),
        preco: Optional[str]            = Form(None),
        disponivel: Optional[bool]      = Form(True),
        image_filenames: Optional[List[str]] = Form(None),
    ) -> "ImovelUpdate":
        return cls(
            titulo=titulo,
            descricao=descricao,
            metragem=metragem,
            quartos=quartos,
            distancia_praia=distancia_praia,
            tipo_aluguel=tipo_aluguel,
            mobilhada=mobilhada,
            preco=preco,
            image_filenames=image_filenames,
            disponivel=disponivel,
        )

    model_config = ConfigDict(extra="forbid")

class ImovelOut(BaseModel):
    id: int
    titulo: str
    descricao: str
    metragem: int
    quartos: int
    distancia_praia: str
    tipo_aluguel: str
    mobilhada: bool
    preco: str
    disponivel: bool

    # pegamos o relacionamento .images do ORM
    # Usamos Field com serialization_alias para manter compatibilidade
    imagens: List[str] = Field(..., alias="images", serialization_alias="imagens")

    @field_validator("imagens", mode="before")
    @classmethod
    def extract_filenames(cls, v):
        if not v:
            return []
        # Se já for uma lista de strings, retorna como está
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], str):
            return v
        # Se for uma lista de objetos Image, extrai os filenames
        return [f"/images/{img.filename}" for img in v]

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


