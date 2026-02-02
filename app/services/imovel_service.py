from typing import List, Optional
from sqlalchemy.orm import Session

from app.models  import imovel_model
from app.schemas import imovel_schema
from app.core.cache import cached, clear_cache

# CRUD Imóvel
def criar_imovel(
    db: Session,
    imovel_in: imovel_schema.ImovelCreate,
    image_filenames: Optional[List[str]] = None
) -> imovel_model.Imovel:
    try:
        # cria o objeto Imovel
        imovel_data = imovel_in.model_dump()
        db_imovel = imovel_model.Imovel(**imovel_data)
        db.add(db_imovel)
        db.commit()
        db.refresh(db_imovel)

        # só depois de ter o ID, adiciona as imagens
        if image_filenames:
            try:
                for fname in image_filenames:
                    img = imovel_model.Image(filename=fname, imovel_id=db_imovel.id)
                    db.add(img)
                db.commit()
                db.refresh(db_imovel)
            except Exception:
                db.rollback()
                raise
        
        # Limpa cache de listagem de imóveis
        clear_cache("imoveis:")

        return db_imovel
    except Exception:
        db.rollback()
        raise

def listar_imoveis(db: Session):
    return db.query(imovel_model.Imovel).all()

def obter_imovel_por_id(db: Session, imovel_id: int) -> imovel_model.Imovel:
    """Obtém um imóvel específico por ID com imagens carregadas"""
    from sqlalchemy.orm import joinedload
    imovel = db.query(imovel_model.Imovel).options(joinedload(imovel_model.Imovel.images)).filter(imovel_model.Imovel.id == imovel_id).first()
    if not imovel:
        raise ValueError("Imóvel não encontrado")
    return imovel

@cached(key_prefix="imoveis")
def listar_imoveis_paginated(
    db: Session, 
    page: int = 1, 
    page_size: int = 10,
    disponivel: Optional[bool] = None,
    distancia_praia: Optional[str] = None,
    quartos: Optional[int] = None,
    tipo_aluguel: Optional[str] = None
):
    """Lista imóveis com paginação e filtros (com cache)"""
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload
    
    query = db.query(imovel_model.Imovel).options(joinedload(imovel_model.Imovel.images))
    
    # Aplicar filtros
    if disponivel is not None:
        query = query.filter(imovel_model.Imovel.disponivel == disponivel)
    if distancia_praia:
        query = query.filter(imovel_model.Imovel.distancia_praia == distancia_praia)
    if quartos is not None:
        query = query.filter(imovel_model.Imovel.quartos >= quartos)
    if tipo_aluguel:
        query = query.filter(imovel_model.Imovel.tipo_aluguel == tipo_aluguel)
    
    # Contar total (sem eager loading para performance)
    total = query.count()
    
    # Aplicar paginação
    offset = (page - 1) * page_size
    imoveis = query.offset(offset).limit(page_size).all()
    
    return imoveis, total

def add_images_to_imovel(db: Session, imovel_id: int, filenames: list[str]):
    try:
        imovel = db.query(imovel_model.Imovel).filter(imovel_model.Imovel.id == imovel_id).first()
        if not imovel:
            raise ValueError("Imóvel não encontrado")
        for fname in filenames:
            img = imovel_model.Image(filename=fname, imovel_id=imovel.id)
            db.add(img)
        db.commit()
        db.refresh(imovel)
        return imovel
    except Exception:
        db.rollback()
        raise


def toggle_imovel_disponibilidade(db: Session, imovel_id: int) -> imovel_model.Imovel:
    try:
        imovel = db.query(imovel_model.Imovel).filter(imovel_model.Imovel.id == imovel_id).first()
        if not imovel:
            raise ValueError("Imóvel não encontrado")
        imovel.disponivel = not imovel.disponivel
        db.commit()
        db.refresh(imovel)
        # Limpa cache de listagem de imóveis
        clear_cache("imoveis:")
        return imovel
    except Exception:
        db.rollback()
        raise