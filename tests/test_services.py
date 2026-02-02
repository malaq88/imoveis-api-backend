"""
Testes para os services
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from app.schemas import imovel_schema, user_schema
from app.services import imovel_service, user_service
from app.core.dependencies import pwd_context

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


class TestUserService:
    """Testes para user_service"""
    
    def test_get_user_by_username_exists(self, db_session):
        """Testa busca de usuário existente por username"""
        user_in = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user_in)
        
        found_user = user_service.get_user_by_username(db_session, "testuser")
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "testuser"
    
    def test_get_user_by_username_not_exists(self, db_session):
        """Testa busca de usuário inexistente"""
        user = user_service.get_user_by_username(db_session, "nonexistent")
        assert user is None
    
    def test_get_user_by_email_exists(self, db_session):
        """Testa busca de usuário existente por email"""
        user_in = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        created_user = user_service.create_user(db_session, user_in)
        
        found_user = user_service.get_user_by_email(db_session, "test@example.com")
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "test@example.com"
    
    def test_get_user_by_email_not_exists(self, db_session):
        """Testa busca de usuário por email inexistente"""
        user = user_service.get_user_by_email(db_session, "nonexistent@example.com")
        assert user is None
    
    def test_create_user_password_hash(self, db_session):
        """Testa que a senha é hasheada corretamente"""
        user_in = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        user = user_service.create_user(db_session, user_in)
        
        assert user.hashed_password != user_in.password
        assert pwd_context.verify("password123", user.hashed_password)
        assert not pwd_context.verify("wrong_password", user.hashed_password)
    
    def test_create_user_defaults(self, db_session):
        """Testa valores padrão ao criar usuário"""
        user_in = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        user = user_service.create_user(db_session, user_in)
        
        assert user.disabled is False
        assert user.is_admin is False
    
    def test_create_user_admin(self, db_session):
        """Testa criação de usuário admin"""
        user_in = user_schema.UserCreate(
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            password="password123",
            is_admin=True
        )
        user = user_service.create_user(db_session, user_in)
        
        assert user.is_admin is True
    
    def test_delete_user_exists(self, db_session):
        """Testa deleção de usuário existente"""
        user_in = user_schema.UserCreate(
            username="todelete",
            email="delete@example.com",
            full_name="To Delete",
            password="password123",
            is_admin=False
        )
        user = user_service.create_user(db_session, user_in)
        user_id = user.id
        
        result = user_service.delete_user(db_session, user_id)
        assert result is True
        
        # Verificar que foi deletado
        deleted_user = user_service.get_user_by_username(db_session, "todelete")
        assert deleted_user is None
    
    def test_delete_user_not_exists(self, db_session):
        """Testa deleção de usuário inexistente"""
        result = user_service.delete_user(db_session, 99999)
        assert result is False
    
    def test_list_users_paginated(self, db_session):
        """Testa listagem paginada de usuários"""
        # Criar vários usuários
        for i in range(10):
            user_in = user_schema.UserCreate(
                username=f"user{i}",
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                password="password123",
                is_admin=False
            )
            user_service.create_user(db_session, user_in)
        
        # Testar primeira página
        users, total = user_service.list_users_paginated(db_session, page=1, page_size=5)
        assert len(users) == 5
        assert total == 10
        
        # Testar segunda página
        users, total = user_service.list_users_paginated(db_session, page=2, page_size=5)
        assert len(users) == 5
        assert total == 10
        
        # Testar página vazia
        users, total = user_service.list_users_paginated(db_session, page=3, page_size=5)
        assert len(users) == 0
        assert total == 10


class TestImovelService:
    """Testes para imovel_service"""
    
    def test_criar_imovel_basic(self, db_session):
        """Testa criação básica de imóvel"""
        imovel_in = imovel_schema.ImovelCreate(
            titulo="Apartamento Teste",
            descricao="Descrição do apartamento",
            metragem=80,
            quartos=2,
            distancia_praia="200m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="500.00",
            disponivel=True
        )
        imovel = imovel_service.criar_imovel(db_session, imovel_in)
        
        assert imovel.id is not None
        assert imovel.titulo == imovel_in.titulo
        assert imovel.descricao == imovel_in.descricao
        assert imovel.metragem == imovel_in.metragem
        assert imovel.quartos == imovel_in.quartos
        assert imovel.distancia_praia == imovel_in.distancia_praia
        assert imovel.tipo_aluguel == imovel_in.tipo_aluguel
        assert imovel.mobilhada == imovel_in.mobilhada
        assert imovel.preco == imovel_in.preco
        assert imovel.disponivel == imovel_in.disponivel
    
    def test_criar_imovel_com_imagens(self, db_session):
        """Testa criação de imóvel com imagens"""
        imovel_in = imovel_schema.ImovelCreate(
            titulo="Casa Teste",
            descricao="Descrição da casa",
            metragem=120,
            quartos=3,
            distancia_praia="100m",
            tipo_aluguel="Mensal",
            mobilhada=False,
            preco="1000.00",
            disponivel=True
        )
        filenames = ["img1.jpg", "img2.png", "img3.jpg"]
        imovel = imovel_service.criar_imovel(db_session, imovel_in, image_filenames=filenames)
        
        assert len(imovel.images) == 3
        assert {img.filename for img in imovel.images} == set(filenames)
    
    def test_listar_imoveis_paginated(self, db_session):
        """Testa listagem paginada de imóveis"""
        # Criar vários imóveis
        for i in range(15):
            imovel_in = imovel_schema.ImovelCreate(
                titulo=f"Imóvel {i}",
                descricao=f"Descrição {i}",
                metragem=50 + i * 5,
                quartos=1 + (i % 3),
                distancia_praia="500m",
                tipo_aluguel="Diária",
                mobilhada=True,
                preco=f"{100 + i * 10}.00",
                disponivel=True
            )
            imovel_service.criar_imovel(db_session, imovel_in)
        
        # Testar primeira página
        imoveis, total = imovel_service.listar_imoveis_paginated(
            db_session, page=1, page_size=10, disponivel=True
        )
        assert len(imoveis) == 10
        assert total == 15
        
        # Testar segunda página
        imoveis, total = imovel_service.listar_imoveis_paginated(
            db_session, page=2, page_size=10, disponivel=True
        )
        assert len(imoveis) == 5
        assert total == 15
    
    def test_listar_imoveis_filtros(self, db_session):
        """Testa listagem de imóveis com filtros"""
        # Criar imóveis com diferentes características
        imovel1 = imovel_schema.ImovelCreate(
            titulo="Imóvel 1",
            descricao="Descrição 1",
            metragem=50,
            quartos=2,
            distancia_praia="500m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="500.00",
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
            preco="1000.00",
            disponivel=True
        )
        imovel_service.criar_imovel(db_session, imovel2)
        
        imovel3 = imovel_schema.ImovelCreate(
            titulo="Imóvel 3",
            descricao="Descrição 3",
            metragem=100,
            quartos=2,
            distancia_praia="500m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="800.00",
            disponivel=False  # Indisponível
        )
        imovel_service.criar_imovel(db_session, imovel3)
        
        # Testar filtro por disponibilidade
        imoveis, total = imovel_service.listar_imoveis_paginated(
            db_session, disponivel=True
        )
        assert total == 2
        assert all(imovel.disponivel for imovel in imoveis)
        
        imoveis, total = imovel_service.listar_imoveis_paginated(
            db_session, disponivel=False
        )
        assert total == 1
        assert all(not imovel.disponivel for imovel in imoveis)
        
        # Testar filtro por quartos
        imoveis, total = imovel_service.listar_imoveis_paginated(
            db_session, quartos=3, disponivel=True
        )
        assert total == 1
        assert all(imovel.quartos >= 3 for imovel in imoveis)
        
        # Testar filtro por distancia_praia
        imoveis, total = imovel_service.listar_imoveis_paginated(
            db_session, distancia_praia="500m", disponivel=True
        )
        assert total == 1
        assert all(imovel.distancia_praia == "500m" for imovel in imoveis)
        
        # Testar filtro por tipo_aluguel
        imoveis, total = imovel_service.listar_imoveis_paginated(
            db_session, tipo_aluguel="Diária", disponivel=True
        )
        assert total == 1
        assert all(imovel.tipo_aluguel == "Diária" for imovel in imoveis)
    
    def test_add_images_to_imovel(self, db_session):
        """Testa adicionar imagens a um imóvel existente"""
        imovel_in = imovel_schema.ImovelCreate(
            titulo="Imóvel Teste",
            descricao="Descrição",
            metragem=60,
            quartos=2,
            distancia_praia="300m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="600.00",
            disponivel=True
        )
        imovel = imovel_service.criar_imovel(db_session, imovel_in)
        
        assert len(imovel.images) == 0
        
        # Adicionar imagens
        filenames = ["new1.jpg", "new2.png"]
        updated = imovel_service.add_images_to_imovel(db_session, imovel.id, filenames)
        
        assert len(updated.images) == 2
        assert {img.filename for img in updated.images} == set(filenames)
    
    def test_add_images_to_imovel_not_found(self, db_session):
        """Testa adicionar imagens a imóvel inexistente"""
        with pytest.raises(ValueError, match="Imóvel não encontrado"):
            imovel_service.add_images_to_imovel(db_session, 99999, ["img.jpg"])
    
    def test_toggle_imovel_disponibilidade(self, db_session):
        """Testa alternar disponibilidade de imóvel"""
        imovel_in = imovel_schema.ImovelCreate(
            titulo="Imóvel Teste",
            descricao="Descrição",
            metragem=70,
            quartos=2,
            distancia_praia="400m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="700.00",
            disponivel=True
        )
        imovel = imovel_service.criar_imovel(db_session, imovel_in)
        assert imovel.disponivel is True
        
        # Alternar para indisponível
        updated = imovel_service.toggle_imovel_disponibilidade(db_session, imovel.id)
        assert updated.disponivel is False
        
        # Alternar de volta para disponível
        updated = imovel_service.toggle_imovel_disponibilidade(db_session, imovel.id)
        assert updated.disponivel is True
    
    def test_toggle_imovel_disponibilidade_not_found(self, db_session):
        """Testa alternar disponibilidade de imóvel inexistente"""
        with pytest.raises(ValueError, match="Imóvel não encontrado"):
            imovel_service.toggle_imovel_disponibilidade(db_session, 99999)

