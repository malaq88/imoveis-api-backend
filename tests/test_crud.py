import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.schemas import imovel_schema, user_schema
from app.services import imovel_service, user_service

# Use in-memory SQLite database for tests
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Create tables
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)

# CRUD Imóvel Tests

def test_criar_imovel_sem_imagens(db_session):
    imovel_in = imovel_schema.ImovelCreate(
        titulo="Apto Teste",
        descricao="Descrição teste",
        metragem=100,
        quartos=2,
        distancia_praia="100m",
        tipo_aluguel="diaria",
        mobilhada=True,
        preco=200.0
    )
    imovel = imovel_service.criar_imovel(db_session, imovel_in)
    assert imovel.id is not None
    assert imovel.titulo == imovel_in.titulo
    assert imovel.descricao == imovel_in.descricao
    assert imovel.metragem == imovel_in.metragem
    assert len(imovel.images) == 0


def test_criar_imovel_com_imagens(db_session):
    imovel_in = imovel_schema.ImovelCreate(
        titulo="Casa Teste",
        descricao="Outra descrição",
        metragem=150,
        quartos=3,
        distancia_praia="200m",
        tipo_aluguel="mensal",
        mobilhada=False,
        preco=500.0
    )
    filenames = ["img1.jpg", "img2.png"]
    imovel = imovel_service.criar_imovel(db_session, imovel_in, image_filenames=filenames)
    assert imovel.id is not None
    assert len(imovel.images) == 2
    assert {img.filename for img in imovel.images} == set(filenames)


def test_listar_imoveis(db_session):
    # Create two imóveis
    for i in range(2):
        imovel_in = imovel_schema.ImovelCreate(
            titulo=f"Imovel{i}",
            descricao="Desc",
            metragem=50 + i,
            quartos=1 + i,
            distancia_praia="300m",
            tipo_aluguel="anual",
            mobilhada=True,
            preco=100.0 + i
        )
        imovel_service.criar_imovel(db_session, imovel_in)
    imoveis = imovel_service.listar_imoveis(db_session)
    assert len(imoveis) == 2


def test_add_images_to_imovel(db_session):
    imovel_in = imovel_schema.ImovelCreate(
        titulo="Img Teste",
        descricao="Desc",
        metragem=80,
        quartos=2,
        distancia_praia="50m",
        tipo_aluguel="diaria",
        mobilhada=False,
        preco=300.0
    )
    imovel = imovel_service.criar_imovel(db_session, imovel_in)
    filenames = ["nova1.png"]
    updated = imovel_service.add_images_to_imovel(db_session, imovel.id, filenames)
    assert len(updated.images) == 1
    assert updated.images[0].filename == "nova1.png"


def test_add_images_to_imovel_not_found(db_session):
    with pytest.raises(ValueError):
        imovel_service.add_images_to_imovel(db_session, 999, ["x.jpg"])

# CRUD Usuário Tests

def test_get_user_by_username_none(db_session):
    user = user_service.get_user_by_username(db_session, "usuario_inexistente")
    assert user is None


def test_create_user_and_get(db_session):
    user_in = user_schema.UserCreate(
        username="user1",
        email="user1@example.com",
        full_name="User One",
        password="senha123",
        is_admin=True
    )
    user = user_service.create_user(db_session, user_in)
    # After creation, user should have an ID and hashed password
    assert user.id is not None
    assert user.username == user_in.username
    assert user.email == user_in.email
    assert user.full_name == user_in.full_name
    assert user.hashed_password != user_in.password
    assert user.is_admin is True
    assert user.disabled is False

    # Fetch the same user
    fetched = user_service.get_user_by_username(db_session, user_in.username)
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.username == user.username
    assert fetched.email == user.email
