import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.core.config import settings
from app.models import user_model
from app.schemas import user_schema, pagination_schema
from app.services import user_service
from sqlalchemy.orm import Session
from app.core.dependencies import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY, authenticate_user, get_db, get_current_active_user, get_current_active_admin # type: ignore
from app.core.rate_limit import limiter
from jose import jwt

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["Usuários"],
)

# Token
@router.post(
    "/token",
    response_model=user_schema.Token,
    summary="Autenticação",
    description="Gera token JWT para autenticação na API",
    response_description="Token de acesso JWT",
    responses={
        200: {
            "description": "Token gerado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        401: {
            "description": "Credenciais inválidas",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect username or password"}
                }
            }
        }
    }
)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": user.username, "exp": datetime.now(timezone.utc) + expires},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Usuários
@router.post(
    "/users/",
    response_model=user_schema.UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário",
    description="Cria um novo usuário no sistema. Requer privilégios de administrador.",
    responses={
        201: {
            "description": "Usuário criado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "novousuario",
                        "email": "novo@example.com",
                        "full_name": "Novo Usuário",
                        "disabled": False,
                        "is_admin": False
                    }
                }
            }
        },
        400: {
            "description": "Username ou email já cadastrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Username already registered"}
                }
            }
        },
        403: {
            "description": "Privilégios de administrador necessários"
        }
    }
)
@limiter.limit("5/minute")
def create_user(
    request: Request,
    user_in: user_schema.UserCreate,
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_admin)
):
    if user_service.get_user_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if user_service.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_service.create_user(db, user_in)

@router.get(
    "/users/",
    response_model=pagination_schema.PaginatedResponse[user_schema.UserOut],
    summary="Listar usuários",
    description="Lista todos os usuários do sistema com paginação. Requer privilégios de administrador.",
    responses={
        200: {
            "description": "Lista de usuários paginada",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "username": "admin",
                                "email": "admin@example.com",
                                "full_name": "Administrador",
                                "disabled": False,
                                "is_admin": True
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 10,
                        "total_pages": 1
                    }
                }
            }
        },
        403: {
            "description": "Privilégios de administrador necessários"
        }
    }
)
@limiter.limit("30/minute")
def list_users(
    request: Request,
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(None, ge=1, le=settings.MAX_PAGE_SIZE, description="Itens por página"),
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_admin)
):
    """Lista usuários com paginação"""
    if page_size is None:
        page_size = settings.DEFAULT_PAGE_SIZE
    
    users, total = user_service.list_users_paginated(db, page=page, page_size=page_size)
    logger.info(f"Listando usuários: página {page}, tamanho {page_size}, total {total}")
    
    return pagination_schema.PaginatedResponse.create(
        items=users,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get(
    "/users/me",
    response_model=user_schema.UserOut,
    summary="Obter usuário atual",
    description="Retorna os dados do usuário autenticado",
    responses={
        200: {
            "description": "Dados do usuário autenticado",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "usuario",
                        "email": "usuario@example.com",
                        "full_name": "Usuário",
                        "disabled": False,
                        "is_admin": False
                    }
                }
            }
        },
        401: {
            "description": "Não autenticado"
        }
    }
)
def read_users_me(
    current_user: user_model.User = Depends(get_current_active_user)
):
    return current_user

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_active_admin)]
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    if not user_service.delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)