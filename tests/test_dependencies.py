"""
Testes para dependencies (autenticação, etc)
"""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt
from database import Base
from app.models import user_model
from app.schemas import user_schema
from app.services import user_service
from app.core.dependencies import (
    get_db,
    verify_password,
    authenticate_user,
    get_current_user,
    get_current_active_user,
    get_current_active_admin
)
from app.core.config import settings

# Use in-memory SQLite database for tests
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Cria uma sessão de banco de dados para cada teste"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=engine)


class TestPasswordVerification:
    """Testes para verificação de senha"""
    
    def test_verify_password_correct(self):
        """Testa verificação de senha correta"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "test_password"
        hashed = pwd_context.hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Testa verificação de senha incorreta"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "test_password"
        hashed = pwd_context.hash(password)
        
        assert verify_password("wrong_password", hashed) is False


class TestAuthentication:
    """Testes para autenticação"""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session):
        """Testa autenticação bem-sucedida"""
        user_in = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        user_service.create_user(db_session, user_in)
        
        user = await authenticate_user(db_session, "testuser", "password123")
        assert user is not None
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session):
        """Testa autenticação com senha incorreta"""
        user_in = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        user_service.create_user(db_session, user_in)
        
        user = await authenticate_user(db_session, "testuser", "wrong_password")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_exists(self, db_session):
        """Testa autenticação de usuário inexistente"""
        user = await authenticate_user(db_session, "nonexistent", "password123")
        assert user is None


class TestGetCurrentUser:
    """Testes para get_current_user"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, db_session):
        """Testa obtenção de usuário com token válido"""
        user_in = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user_in)
        
        # Criar token válido
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = jwt.encode(
            {"sub": created_user.username, "exp": datetime.now(timezone.utc) + expires},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Mock do Depends para o token
        from unittest.mock import Mock
        mock_token = Mock(return_value=token)
        
        user = await get_current_user(token=token, db=db_session)
        assert user is not None
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db_session):
        """Testa obtenção de usuário com token inválido"""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid_token", db=db_session)
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, db_session):
        """Testa obtenção de usuário com token expirado"""
        user_in = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user_in)
        
        # Criar token expirado
        expires = timedelta(minutes=-1)  # Expirado
        token = jwt.encode(
            {"sub": created_user.username, "exp": datetime.now(timezone.utc) + expires},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(self, db_session):
        """Testa obtenção de usuário que não existe mais"""
        # Criar token para usuário que não existe
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = jwt.encode(
            {"sub": "nonexistent", "exp": datetime.now(timezone.utc) + expires},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 401


class TestGetCurrentActiveUser:
    """Testes para get_current_active_user"""
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_active(self, db_session):
        """Testa obtenção de usuário ativo"""
        user_in = user_schema.UserCreate(
            username="activeuser",
            email="active@example.com",
            full_name="Active User",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user_in)
        
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = jwt.encode(
            {"sub": created_user.username, "exp": datetime.now(timezone.utc) + expires},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        current_user = await get_current_user(token=token, db=db_session)
        active_user = await get_current_active_user(current_user=current_user)
        
        assert active_user.username == "activeuser"
        assert active_user.disabled is False
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_disabled(self, db_session):
        """Testa obtenção de usuário desabilitado"""
        user_in = user_schema.UserCreate(
            username="disableduser",
            email="disabled@example.com",
            full_name="Disabled User",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user_in)
        created_user.disabled = True
        db_session.commit()
        
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = jwt.encode(
            {"sub": created_user.username, "exp": datetime.now(timezone.utc) + expires},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        current_user = await get_current_user(token=token, db=db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user=current_user)
        assert exc_info.value.status_code == 400
        assert "Inactive user" in exc_info.value.detail


class TestGetCurrentActiveAdmin:
    """Testes para get_current_active_admin"""
    
    @pytest.mark.asyncio
    async def test_get_current_active_admin_success(self, db_session):
        """Testa obtenção de admin ativo"""
        user_in = user_schema.UserCreate(
            username="adminuser",
            email="admin@example.com",
            full_name="Admin User",
            password="password123",
            is_admin=True
        )
        created_user = user_service.create_user(db_session, user_in)
        
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = jwt.encode(
            {"sub": created_user.username, "exp": datetime.now(timezone.utc) + expires},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        current_user = await get_current_user(token=token, db=db_session)
        active_user = await get_current_active_user(current_user=current_user)
        admin_user = await get_current_active_admin(current_user=active_user)
        
        assert admin_user.username == "adminuser"
        assert admin_user.is_admin is True
    
    @pytest.mark.asyncio
    async def test_get_current_active_admin_non_admin(self, db_session):
        """Testa obtenção de admin com usuário não-admin"""
        user_in = user_schema.UserCreate(
            username="regularuser",
            email="regular@example.com",
            full_name="Regular User",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user_in)
        
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = jwt.encode(
            {"sub": created_user.username, "exp": datetime.now(timezone.utc) + expires},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        current_user = await get_current_user(token=token, db=db_session)
        active_user = await get_current_active_user(current_user=current_user)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_admin(current_user=active_user)
        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in exc_info.value.detail

