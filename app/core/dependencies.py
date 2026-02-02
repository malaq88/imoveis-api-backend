# Dependência para sessão do banco de dados
import logging
import os
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from database import SessionLocal
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from contextlib import asynccontextmanager
from app.models import user_model
from app.schemas import user_schema
from app.services import user_service

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# Lifespan handler para startup (cria admin) e shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        if not user_service.get_user_by_username(db, settings.ADMIN_USERNAME):
            admin_in = user_schema.UserCreate(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                full_name="Administrador",
                password=settings.ADMIN_PASSWORD,
                is_admin=True
            )
            try:
                user_service.create_user(db, admin_in)
                logger.info(f"Usuário admin '{settings.ADMIN_USERNAME}' criado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao criar usuário admin: {e}", exc_info=True)
                raise
    except Exception as e:
        logger.error(f"Erro no startup: {e}", exc_info=True)
        raise
    finally:
        db.close()
    yield

# Configurações carregadas do .env
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_user(db: Session, username: str, password: str):
    user = user_service.get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> user_model.User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = user_service.get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: user_model.User = Depends(get_current_user)
) -> user_model.User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_admin(
    current_user: user_model.User = Depends(get_current_active_user)
) -> user_model.User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user
