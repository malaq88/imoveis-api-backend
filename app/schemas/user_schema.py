from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

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

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str


class DeleteResponse(BaseModel):
    detail: str