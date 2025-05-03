from typing import List, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app import models, schemas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# CRUD Imóvel
def criar_imovel(
    db: Session,
    imovel_in: schemas.ImovelCreate,
    image_filenames: Optional[List[str]] = None
) -> models.Imovel:
    # cria o objeto Imovel
    db_imovel = models.Imovel(**imovel_in.dict())
    db.add(db_imovel)
    db.commit()
    db.refresh(db_imovel)

    # só depois de ter o ID, adiciona as imagens
    if image_filenames:
        for fname in image_filenames:
            img = models.Image(filename=fname, imovel_id=db_imovel.id)
            db.add(img)
        db.commit()
        db.refresh(db_imovel)

    return db_imovel

def listar_imoveis(db: Session):
    return db.query(models.Imovel).all()

def add_images_to_imovel(db: Session, imovel_id: int, filenames: list[str]):
    imovel = db.query(models.Imovel).get(imovel_id)
    if not imovel:
        raise ValueError("Imóvel não encontrado")
    for fname in filenames:
        img = models.Image(filename=fname, imovel_id=imovel.id)
        db.add(img)
    db.commit()
    db.refresh(imovel)
    return imovel

# CRUD Usuário

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user_in: schemas.UserCreate):
    hashed_password = pwd_context.hash(user_in.password)
    db_user = models.User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        disabled=False,
        is_admin=user_in.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def toggle_imovel_disponibilidade(db: Session, imovel_id: int) -> models.Imovel:
    imovel = db.query(models.Imovel).filter(models.Imovel.id == imovel_id).first()
    if not imovel:
        raise ValueError("Imóvel não encontrado")
    imovel.disponivel = not imovel.disponivel
    db.commit()
    db.refresh(imovel)
    return imovel