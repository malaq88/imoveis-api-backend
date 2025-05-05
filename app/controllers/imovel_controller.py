# Imóveis - listagem
import os
from typing import List, Optional
import uuid

import aiofiles
from fastapi import Depends, File, UploadFile

from app.core.dependencies import get_db, get_current_active_user, validar_tipo, IMAGES_DIR
from fastapi import APIRouter, HTTPException, Path
from app.models import imovel_model, user_model
from app.schemas import imovel_schema
from sqlalchemy.orm import Session

from app.services import imovel_service

router = APIRouter(
    prefix="",
    tags=["Imóveis"],
)


@router.get("/imoveis", response_model=List[imovel_schema.ImovelOut])
def listar_imoveis(
    distancia_praia: Optional[str] = None,
    quartos: Optional[int] = None,
    tipo_aluguel: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(imovel_model.Imovel)
    if distancia_praia:
        query = query.filter(imovel_model.Imovel.distancia_praia == distancia_praia)
    if quartos is not None:
        query = query.filter(imovel_model.Imovel.quartos >= quartos)
    if tipo_aluguel:
        query = query.filter(imovel_model.Imovel.tipo_aluguel == tipo_aluguel)
    return query.filter(imovel_model.Imovel.disponivel == True).all()

@router.get("/imoveis_indisponiveis", response_model=List[imovel_schema.ImovelOut])
def listar_imoveis(
    distancia_praia: Optional[str] = None,
    quartos: Optional[int] = None,
    tipo_aluguel: Optional[str] = None,
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_user),
):
    query = db.query(imovel_model.Imovel)
    if distancia_praia:
        query = query.filter(imovel_model.Imovel.distancia_praia == distancia_praia)
    if quartos is not None:
        query = query.filter(imovel_model.Imovel.quartos >= quartos)
    if tipo_aluguel:
        query = query.filter(imovel_model.Imovel.tipo_aluguel == tipo_aluguel)
    return query.filter(imovel_model.Imovel.disponivel == False).all()

# Imóveis - criação
@router.post("/imoveis", response_model=imovel_schema.ImovelOut)
async def criar_imovel(
    imovel: imovel_schema.ImovelCreate = Depends(imovel_schema.ImovelCreate.as_form),
    imagens: List[UploadFile]     = File(...),
    db: Session                  = Depends(get_db),
    _: user_model.User               = Depends(get_current_active_user),
):
    saved_filenames: List[str] = []
    for file in imagens:
        validar_tipo(file)
        ext = os.path.splitext(file.filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(IMAGES_DIR, unique_name)
        async with aiofiles.open(dest, "wb") as out:
            await out.write(await file.read())
        saved_filenames.append(unique_name)

    im = imovel_service.criar_imovel(db, imovel, image_filenames=saved_filenames)
    return im

# Imóveis - atualização (multipart/form-data)
@router.put("/imoveis/{imovel_id}", response_model=imovel_schema.ImovelOut)
async def update_imovel(
    imovel_id: int,
    imovel_in: imovel_schema.ImovelUpdate                = Depends(imovel_schema.ImovelUpdate.as_form),
    novas_imagens: List[UploadFile]        = File(None),
    db: Session                            = Depends(get_db),
    _: user_model.User                         = Depends(get_current_active_user),
):
    db_imovel = db.query(imovel_model.Imovel).filter(imovel_model.Imovel.id == imovel_id).first()
    if not db_imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    # 1) salva uploads novos (se houver)
    saved_filenames: List[str] = []
    if novas_imagens:
        for file in novas_imagens:
            validar_tipo(file)
            ext = os.path.splitext(file.filename)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            dest = os.path.join(IMAGES_DIR, unique_name)
            async with aiofiles.open(dest, "wb") as out:
                await out.write(await file.read())
            saved_filenames.append(unique_name)

    # 2) atualiza campos não-nulos
    update_data = imovel_in.dict(exclude_unset=True, exclude={"image_filenames"})
    for field, value in update_data.items():
        setattr(db_imovel, field, value)

    # 3) associa as imagens recém-salvas
    for fn in saved_filenames:
        db_imovel.images.append(imovel_schema.Image(filename=fn))

    db.commit()
    db.refresh(db_imovel)
    return db_imovel

# Upload de imagens extra
@router.post("/imoveis/{imovel_id}/images", response_model=imovel_schema.ImovelOut)
async def upload_images_para_imovel(
    imovel_id: int = Path(..., description="ID do imóvel"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_user)
):
    saved = []
    for file in files:
        validar_tipo(file)
        ext = os.path.splitext(file.filename)[1]
        name = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(IMAGES_DIR, name)
        async with aiofiles.open(path, "wb") as out_file:
            await out_file.write(await file.read())
        saved.append(name)
    try:
        return imovel_service.add_images_to_imovel(db, imovel_id, saved)
    except ValueError:
        for fn in saved:
            os.remove(os.path.join(IMAGES_DIR, fn))
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

# Servir imagens
@router.get("/images/{filename}")
def serve_image(
    filename: str,
    _: user_model.User = Depends(get_current_active_user)
):
    path = os.path.join(IMAGES_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return FileResponse(path=path)


@router.patch(
    "/imoveis/{imovel_id}/disponibilidade",
    response_model=imovel_schema.ImovelOut,
    summary="Alterna disponibilidade do imóvel"
)
def toggle_disponibilidade(
    imovel_id: int,
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_user)
):
    """
    Se o imóvel estiver disponível, marca como indisponível;
    se estiver indisponível, marca como disponível.
    """
    try:
        im = imovel_service.toggle_imovel_disponibilidade(db, imovel_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return im