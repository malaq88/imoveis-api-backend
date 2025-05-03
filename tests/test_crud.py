import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import crud, models, schemas

# Fixture para uma sessão de banco de dados de teste em memória
@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False
    )
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Testes de usuário

def test_create_and_get_user(session):
    # Cria usuário admin
    user_in = schemas.UserCreate(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password="secret",
        is_admin=True
    )
    user = crud.create_user(session, user_in)
    assert user.id is not None
    assert user.username == "testuser"
    assert user.is_admin is True

    # Busca usuário pelo username
    fetched = crud.get_user_by_username(session, "testuser")
    assert fetched.email == "test@example.com"

# Testes de imóveis

def test_create_and_list_imovel(session):
    imovel_in = schemas.ImovelCreate(
        titulo="Casa Teste",
        descricao="Descrição de teste",
        metragem=120,
        quartos=3,
        distancia_praia="10 min",
        tipo_aluguel="temporada",
        mobilhada=True,
        image_filenames=[]
    )
    imovel = crud.criar_imovel(session, imovel_in)
    assert imovel.id is not None
    assert imovel.quartos == 3

    imoveis = crud.listar_imoveis(session)
    assert len(imoveis) == 1
    assert imoveis[0].titulo == "Casa Teste"

# Teste de associação de imagens

def test_add_images_to_imovel(session):
    # Cria imóvel sem imagens
    imovel_in = schemas.ImovelCreate(
        titulo="Casa Img",
        descricao="Com fotos",
        metragem=80,
        quartos=2,
        distancia_praia="5 min",
        tipo_aluguel="anual",
        mobilhada=False,
        image_filenames=[]
    )
    imovel = crud.criar_imovel(session, imovel_in)
    # Adiciona imagens
    filenames = ["a.png", "b.jpg"]
    updated = crud.add_images_to_imovel(session, imovel.id, filenames)
    # Verifica associação
    imgs = [img.filename for img in updated.images]
    assert set(imgs) == set(filenames)

# Testes adicionais para cobrir todo o crud.py

def test_get_user_by_username_none(session):
    assert crud.get_user_by_username(session, "noexist") is None

def test_create_user_password_and_duplicate(session):
    # Cria primeiro usuário
    user_in = schemas.UserCreate(
        username="dupuser",
        email="dup@example.com",
        full_name="Dup User",
        password="pass",
        is_admin=False
    )
    user1 = crud.create_user(session, user_in)
    assert user1.id is not None
    # Senha deve estar hasheada e verificável
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    assert pwd_ctx.verify("pass", user1.hashed_password)
    # Tentativa de criar usuário com mesmo username falha
    with pytest.raises(Exception):
        crud.create_user(session, user_in)


def test_add_images_invalid_imovel(session):
    with pytest.raises(ValueError):
        crud.add_images_to_imovel(session, 999, ["x.png"])
