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

class ImovelCreate(BaseModel):
    titulo: str
    descricao: str
    metragem: int
    quartos: int
    distancia_praia: str
    tipo_aluguel: str
    mobilhada: bool
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
    ):
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
    # aqui dizemos: pega do ORM o atributo `images` e popula nossa lista `imagens`
    imagens: List[str] = Field(..., alias="images")

    @validator("imagens", pre=True)
    def extract_filenames(cls, v):
        # v vai ser a lista de Image ORM objects
        return [f"/images/{img.filename}" for img in v]

    class Config:
        orm_mode = True
        # permite popular via o alias (alias="images")
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
