from typing import List, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models  import imovel_model

from app import schemas
from app.schemas import imovel_schema

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# CRUD Imóvel
def criar_imovel(
    db: Session,
    imovel_in: imovel_schema.ImovelCreate,
    image_filenames: Optional[List[str]] = None
) -> imovel_model.Imovel:
    # cria o objeto Imovel
    db_imovel = imovel_model.Imovel(**imovel_in.dict())
    db.add(db_imovel)
    db.commit()
    db.refresh(db_imovel)

    # só depois de ter o ID, adiciona as imagens
    if image_filenames:
        for fname in image_filenames:
            img = imovel_model.Image(filename=fname, imovel_id=db_imovel.id)
            db.add(img)
        db.commit()
        db.refresh(db_imovel)

    return db_imovel

def listar_imoveis(db: Session):
    return db.query(imovel_model.Imovel).all()

def add_images_to_imovel(db: Session, imovel_id: int, filenames: list[str]):
    imovel = db.query(imovel_model.Imovel).get(imovel_id)
    if not imovel:
        raise ValueError("Imóvel não encontrado")
    for fname in filenames:
        img = imovel_model.Image(filename=fname, imovel_id=imovel.id)
        db.add(img)
    db.commit()
    db.refresh(imovel)
    return imovel


def toggle_imovel_disponibilidade(db: Session, imovel_id: int) -> imovel_model.Imovel:
    imovel = db.query(imovel_model.Imovel).filter(imovel_model.Imovel.id == imovel_id).first()
    if not imovel:
        raise ValueError("Imóvel não encontrado")
    imovel.disponivel = not imovel.disponivel
    db.commit()
    db.refresh(imovel)
    return imovel