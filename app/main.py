from contextlib import asynccontextmanager
from app.controllers import imovel_controller, user_controller

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.dependencies import lifespan
from app.core.settings import settings
from app.core.database import SessionLocal, engine, Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Cria tabelas no banco
Base.metadata.create_all(bind=engine)

# Cria a aplicação FastAPI com lifespan
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---
app.include_router(user_controller.router, prefix="", tags=["Usuários"])
app.include_router(imovel_controller.router, prefix="", tags=["Imóveis"])