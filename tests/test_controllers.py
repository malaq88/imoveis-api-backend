"""
Testes para os controllers da API
"""
import pytest
import os
import tempfile
import atexit
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Banco de dados de teste em memória
# Usa um arquivo temporário para garantir que as tabelas persistam entre conexões
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
temp_db.close()
SQLALCHEMY_DATABASE_URL = f"sqlite:///{temp_db.name}"

# Limpa o arquivo temporário ao final
def cleanup_temp_db():
    try:
        os.unlink(temp_db.name)
    except:
        pass
atexit.register(cleanup_temp_db)

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override do database.engine ANTES de importar app para que o lifespan use o banco de teste
import database
from database import Base
database.engine = engine
database.SessionLocal = TestingSessionLocal

# Garante que os modelos sejam importados para registrar as tabelas
from app.models import user_model, imovel_model

# Cria as tabelas IMEDIATAMENTE para que o lifespan possa usá-las quando app for importado
Base.metadata.create_all(bind=engine)

# Agora importa o app (que executará o lifespan usando o banco de teste)
from app.main import app
from app.core.dependencies import get_db, pwd_context
from app.core.config import settings
from app.services import user_service
from app.schemas import user_schema

# Desabilita rate limiting e cache para testes
# Isso é feito no conftest.py através de variáveis de ambiente

# Flag para garantir que as tabelas sejam criadas apenas uma vez
_tables_created = True

def ensure_tables():
    """Garante que as tabelas existam no banco de dados"""
    global _tables_created
    if not _tables_created:
        Base.metadata.create_all(bind=engine)
        _tables_created = True

@pytest.fixture(scope="function", autouse=True)
def disable_rate_limiting():
    """Desabilita rate limiting para todos os testes"""
    settings.RATE_LIMIT_ENABLED = False
    # Remove o limiter do app.state
    if hasattr(app.state, 'limiter'):
        app.state.limiter = None
    # Limpa o storage do limiter se existir
    try:
        from app.core.rate_limit import limiter
        if hasattr(limiter, '_storage') and limiter._storage:
            try:
                limiter._storage.clear()
            except:
                pass
    except:
        pass
    yield
    # Limpa novamente após o teste
    try:
        from app.core.rate_limit import limiter
        if hasattr(limiter, '_storage') and limiter._storage:
            try:
                limiter._storage.clear()
            except:
                pass
    except:
        pass

def override_get_db():
    """Override da dependência get_db para testes"""
    # Garante que as tabelas existam antes de criar a sessão
    ensure_tables()
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Cria uma sessão de banco de dados para cada teste"""
    # Garante que as tabelas existam
    ensure_tables()
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()
        # Limpa os dados entre testes (mas mantém as tabelas)
        # Não dropa as tabelas para evitar problemas com o lifespan
        from app.models import user_model, imovel_model
        db_cleanup = TestingSessionLocal()
        try:
            db_cleanup.query(imovel_model.Image).delete()
            db_cleanup.query(imovel_model.Imovel).delete()
            db_cleanup.query(user_model.User).delete()
            db_cleanup.commit()
        except:
            db_cleanup.rollback()
        finally:
            db_cleanup.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Cria um cliente de teste"""
    # Garante que as tabelas existam antes de criar o cliente
    ensure_tables()
    
    # Override do get_db para usar o banco de teste
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db_session):
    """Cria um usuário admin para testes"""
    # Verifica se o admin já existe (criado pelo lifespan)
    existing_admin = user_service.get_user_by_username(db_session, "admin_test")
    if existing_admin:
        return existing_admin
    
    # Verifica se existe admin com o email (pode ter sido criado pelo lifespan com outro username)
    existing_by_email = user_service.get_user_by_email(db_session, "admin@test.com")
    if existing_by_email:
        # Se existe mas com username diferente, atualiza
        if existing_by_email.username != "admin_test":
            existing_by_email.username = "admin_test"
            db_session.commit()
            db_session.refresh(existing_by_email)
        return existing_by_email
    
    # Cria novo admin
    admin = user_schema.UserCreate(
        username="admin_test",
        email="admin@test.com",
        full_name="Admin Test",
        password="admin123",
        is_admin=True
    )
    try:
        return user_service.create_user(db_session, admin)
    except Exception:
        # Se falhar (ex: constraint), busca novamente
        db_session.rollback()
        existing = user_service.get_user_by_username(db_session, "admin_test") or \
                   user_service.get_user_by_email(db_session, "admin@test.com")
        if existing:
            return existing
        raise


@pytest.fixture(scope="function")
def admin_token(client, admin_user):
    """Obtém token de autenticação do admin"""
    response = client.post(
        "/token",
        data={"username": "admin_test", "password": "admin123"}
    )
    
    assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
    data = response.json()
    assert "access_token" in data, f"Response missing access_token: {data}"
    return data["access_token"]


class TestUserController:
    """Testes para o controller de usuários"""
    
    def test_login_success(self, client, admin_user):
        """Testa login bem-sucedido"""
        response = client.post(
            "/token",
            data={"username": "admin_test", "password": "admin123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client, admin_user):
        """Testa login com credenciais inválidas"""
        response = client.post(
            "/token",
            data={"username": "admin_test", "password": "wrong_password"}
        )
        assert response.status_code == 401
    
    def test_create_user(self, client, admin_token):
        """Testa criação de usuário"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        user_data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "full_name": "New User",
            "password": "password123",
            "is_admin": False
        }
        response = client.post("/users/", json=user_data, headers=headers)
        assert response.status_code == 201  # Criado
        assert response.json()["username"] == "newuser"
        assert response.json()["email"] == "newuser@test.com"
    
    def test_create_user_duplicate_email(self, client, admin_token, admin_user):
        """Testa criação de usuário com email duplicado"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        user_data = {
            "username": "different_user",
            "email": "admin@test.com",  # Email duplicado
            "full_name": "Different User",
            "password": "password123",
            "is_admin": False
        }
        response = client.post("/users/", json=user_data, headers=headers)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_create_user_unauthorized(self, client, db_session):
        """Testa criação de usuário sem autenticação"""
        user_data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "full_name": "New User",
            "password": "password123",
            "is_admin": False
        }
        response = client.post("/users/", json=user_data)
        assert response.status_code == 401
    
    def test_create_user_non_admin(self, client, db_session):
        """Testa criação de usuário por usuário não-admin"""
        # Criar usuário não-admin
        user = user_schema.UserCreate(
            username="regular_user",
            email="regular@test.com",
            full_name="Regular User",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user)
        
        # Fazer login
        login_response = client.post(
            "/token",
            data={"username": "regular_user", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Tentar criar usuário
        headers = {"Authorization": f"Bearer {token}"}
        user_data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "full_name": "New User",
            "password": "password123",
            "is_admin": False
        }
        response = client.post("/users/", json=user_data, headers=headers)
        assert response.status_code == 403
    
    def test_create_user_duplicate_username(self, client, admin_token, admin_user):
        """Testa criação de usuário com username duplicado"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        user_data = {
            "username": "admin_test",
            "email": "different@test.com",
            "full_name": "Different User",
            "password": "password123",
            "is_admin": False
        }
        response = client.post("/users/", json=user_data, headers=headers)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_list_users_paginated(self, client, admin_token, db_session):
        """Testa listagem paginada de usuários"""
        # Criar alguns usuários
        for i in range(5):
            user = user_schema.UserCreate(
                username=f"user{i}",
                email=f"user{i}@test.com",
                full_name=f"User {i}",
                password="password123",
                is_admin=False
            )
            user_service.create_user(db_session, user)
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/users/?page=1&page_size=3", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 3
    
    def test_get_current_user(self, client, admin_token):
        """Testa obtenção do usuário atual"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["username"] == "admin_test"
    
    def test_get_current_user_unauthorized(self, client):
        """Testa obtenção do usuário atual sem autenticação"""
        response = client.get("/users/me")
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client):
        """Testa obtenção do usuário atual com token inválido"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 401
    
    def test_delete_user(self, client, admin_token, db_session):
        """Testa deleção de usuário"""
        # Criar usuário para deletar
        user = user_schema.UserCreate(
            username="todelete",
            email="todelete@test.com",
            full_name="To Delete",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user)
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.delete(f"/users/{created_user.id}", headers=headers)
        assert response.status_code == 204
    
    def test_delete_user_not_found(self, client, admin_token):
        """Testa deleção de usuário inexistente"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.delete("/users/99999", headers=headers)
        assert response.status_code == 404
    
    def test_delete_user_unauthorized(self, client, db_session):
        """Testa deleção de usuário sem autenticação"""
        user = user_schema.UserCreate(
            username="todelete",
            email="todelete@test.com",
            full_name="To Delete",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user)
        
        response = client.delete(f"/users/{created_user.id}")
        assert response.status_code == 401


class TestHealthController:
    """Testes para o controller de health check"""
    
    def test_health_check(self, client):
        """Testa health check básico"""
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "database" in data
        assert "cache" in data
    
    def test_readiness_check(self, client):
        """Testa readiness check"""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ready"
    
    def test_liveness_check(self, client):
        """Testa liveness check"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "alive"


class TestImovelController:
    """Testes para o controller de imóveis"""
    
    def test_list_imoveis_empty(self, client):
        """Testa listagem de imóveis vazia"""
        response = client.get("/imoveis")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 0
        assert data["total"] == 0
    
    def test_list_imoveis_paginated(self, client, admin_token, db_session):
        """Testa listagem paginada de imóveis"""
        from app.services import imovel_service
        from app.schemas import imovel_schema
        
        # Criar alguns imóveis
        for i in range(5):
            imovel = imovel_schema.ImovelCreate(
                titulo=f"Imóvel {i}",
                descricao=f"Descrição {i}",
                metragem=50 + i * 10,
                quartos=2 + i,
                distancia_praia="500m",
                tipo_aluguel="Diária",
                mobilhada=True,
                preco="1000.00",
                disponivel=True
            )
            imovel_service.criar_imovel(db_session, imovel)
        
        response = client.get("/imoveis?page=1&page_size=3")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 3
    
    def test_list_imoveis_with_filters(self, client, admin_token, db_session):
        """Testa listagem de imóveis com filtros"""
        from app.services import imovel_service
        from app.schemas import imovel_schema
        
        # Criar imóveis com diferentes características
        imovel1 = imovel_schema.ImovelCreate(
            titulo="Imóvel 1",
            descricao="Descrição 1",
            metragem=50,
            quartos=2,
            distancia_praia="500m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="1000.00",
            disponivel=True
        )
        imovel_service.criar_imovel(db_session, imovel1)
        
        imovel2 = imovel_schema.ImovelCreate(
            titulo="Imóvel 2",
            descricao="Descrição 2",
            metragem=80,
            quartos=3,
            distancia_praia="1km",
            tipo_aluguel="Mensal",
            mobilhada=False,
            preco="2000.00",
            disponivel=True
        )
        imovel_service.criar_imovel(db_session, imovel2)
        
        # Testar filtro por quartos
        response = client.get("/imoveis?quartos=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert all(item["quartos"] >= 3 for item in data["items"])
        
        # Testar filtro por distancia_praia
        response = client.get("/imoveis?distancia_praia=500m")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert all(item["distancia_praia"] == "500m" for item in data["items"])
        
        # Testar filtro por tipo_aluguel
        response = client.get("/imoveis?tipo_aluguel=Diária")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert all(item["tipo_aluguel"] == "Diária" for item in data["items"])
        
        # Testar múltiplos filtros
        response = client.get("/imoveis?quartos=2&tipo_aluguel=Diária")
        assert response.status_code == 200
        data = response.json()
        assert all(item["quartos"] >= 2 and item["tipo_aluguel"] == "Diária" for item in data["items"])
    
    def test_obter_imovel_por_id(self, client, admin_token, db_session):
        """Testa obter um imóvel específico por ID"""
        from app.services import imovel_service
        from app.schemas import imovel_schema
        
        # Criar um imóvel
        imovel = imovel_schema.ImovelCreate(
            titulo="Imóvel Teste",
            descricao="Descrição do imóvel teste",
            metragem=80,
            quartos=2,
            distancia_praia="100m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="500.00",
            disponivel=True
        )
        imovel_criado = imovel_service.criar_imovel(db_session, imovel)
        
        # Obter o imóvel por ID
        response = client.get(f"/imoveis/{imovel_criado.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == imovel_criado.id
        assert data["titulo"] == "Imóvel Teste"
        assert data["descricao"] == "Descrição do imóvel teste"
        assert data["metragem"] == 80
        assert data["quartos"] == 2
        assert data["distancia_praia"] == "100m"
        assert data["tipo_aluguel"] == "Diária"
        assert data["mobilhada"] is True
        assert data["preco"] == "500.00"
        assert data["disponivel"] is True
    
    def test_obter_imovel_por_id_nao_encontrado(self, client):
        """Testa obter um imóvel inexistente"""
        response = client.get("/imoveis/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "não encontrado" in data["detail"].lower()
    
    def test_obter_imovel_por_id_invalido(self, client):
        """Testa obter imóvel com ID inválido"""
        response = client.get("/imoveis/0")
        assert response.status_code == 422  # Validation error
        response = client.get("/imoveis/-1")
        assert response.status_code == 422  # Validation error
    
    def test_create_imovel_requires_auth(self, client):
        """Testa que criação de imóvel requer autenticação"""
        response = client.post("/imoveis")
        assert response.status_code == 401 or response.status_code == 422
    
    def test_get_images_public(self, client):
        """Testa que acesso a imagens é público (não requer autenticação)"""
        # Testa com arquivo inexistente - deve retornar 404, não 401
        response = client.get("/images/test.jpg")
        assert response.status_code == 404  # Arquivo não encontrado, não erro de autenticação
    
    def test_list_imoveis_indisponiveis_requires_auth(self, client):
        """Testa que listagem de imóveis indisponíveis requer autenticação"""
        response = client.get("/imoveis_indisponiveis")
        assert response.status_code == 401
    
    def test_list_imoveis_indisponiveis_with_auth(self, client, admin_token, db_session):
        """Testa listagem de imóveis indisponíveis com autenticação"""
        from app.services import imovel_service
        from app.schemas import imovel_schema
        
        # Criar imóvel indisponível
        imovel = imovel_schema.ImovelCreate(
            titulo="Imóvel Indisponível",
            descricao="Descrição",
            metragem=60,
            quartos=2,
            distancia_praia="300m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="600.00",
            disponivel=False
        )
        imovel_service.criar_imovel(db_session, imovel)
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/imoveis_indisponiveis", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        assert all(item["disponivel"] is False for item in data["items"])
    
    def test_list_users_empty(self, client, admin_token):
        """Testa listagem de usuários vazia (apenas admin)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/users/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # Deve ter pelo menos o admin
        assert len(data["items"]) >= 1

