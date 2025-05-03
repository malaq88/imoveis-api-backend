from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
from fastapi import Form

class ImageOut(BaseModel):
    id: int
    filename: str

    class Config:
        orm_mode = True

class ImovelBase(BaseModel):
    titulo: str
    descricao: str
    metragem: int
    quartos: int
    distancia_praia: str
    tipo_aluguel: str
    mobilhada: bool

class ImovelCreate(ImovelBase):
    preco: float

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
        preco: float          = Form(...),
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
        )

class ImovelUpdate(BaseModel):
    titulo:           Optional[str]      = None
    descricao:        Optional[str]      = None
    metragem:         Optional[int]      = None
    quartos:          Optional[int]      = None
    distancia_praia:  Optional[str]      = None
    tipo_aluguel:     Optional[str]      = None
    mobilhada:        Optional[bool]     = None
    preco:            Optional[float]    = None
    image_filenames:  Optional[List[str]] = None

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
        preco: Optional[float]          = Form(None),
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
        )

    class Config:
        extra = "forbid"

class ImovelOut(BaseModel):
    id: int
    titulo: str
    descricao: str
    metragem: int
    quartos: int
    distancia_praia: str
    tipo_aluguel: str
    mobilhada: bool
    preco: float

    # pegamos o relacionamento .images do ORM
    imagens: List[str] = Field(..., alias="images")

    @validator("imagens", pre=True)
    def extract_filenames(cls, v):
        return [f"/images/{img.filename}" for img in v]

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

# Schemas de usuário
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    is_admin: Optional[bool] = False

class UserOut(UserBase):
    id: int
    disabled: bool
    is_admin: bool

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
