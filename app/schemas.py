from pydantic import BaseModel, EmailStr
from typing import List, Optional

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
    image_filenames: List[str] = []

class ImovelOut(ImovelBase):
    id: int
    images: List[ImageOut] = []

    class Config:
        orm_mode = True

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