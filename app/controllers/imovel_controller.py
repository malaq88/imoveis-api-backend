# Imóveis - listagem
import logging
import os
import re
from typing import List, Optional
import uuid

import aiofiles
from fastapi import Depends, File, UploadFile, Query, Request
from fastapi.responses import FileResponse

from app.core.dependencies import get_db, get_current_active_user
from app.core.config import settings
from app.core.rate_limit import limiter
from fastapi import APIRouter, HTTPException, Path
from app.models import imovel_model, user_model
from app.schemas import imovel_schema, pagination_schema
from sqlalchemy.orm import Session

from app.services import imovel_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["Imóveis"],
)

# Diretório para armazenar imagens
IMAGES_DIR = settings.IMAGES_DIR
os.makedirs(IMAGES_DIR, exist_ok=True)

# Tamanho máximo de arquivo em bytes
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024

def validar_tipo(file: UploadFile):
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Apenas JPEG ou PNG são aceitos")

async def validar_tamanho(file: UploadFile):
    """Valida o tamanho do arquivo"""
    content = await file.read()
    await file.seek(0)  # Reset para o início do arquivo
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Arquivo muito grande. Tamanho máximo: {settings.MAX_FILE_SIZE_MB}MB"
        )

def validar_filename(filename: str) -> str:
    """
    Valida e sanitiza o nome do arquivo para prevenir path traversal.
    
    Args:
        filename: Nome do arquivo a ser validado
        
    Returns:
        Nome do arquivo sanitizado
        
    Raises:
        HTTPException: Se o nome do arquivo contiver caracteres perigosos
    """
    # Remove componentes de caminho perigosos
    safe_name = os.path.basename(filename)
    
    # Valida que não contém caracteres perigosos
    if '..' in safe_name or '/' in safe_name or '\\' in safe_name:
        raise HTTPException(
            status_code=400, 
            detail="Nome de arquivo inválido: contém caracteres perigosos"
        )
    
    # Remove caracteres não permitidos
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', safe_name)
    
    if not safe_name:
        raise HTTPException(
            status_code=400,
            detail="Nome de arquivo inválido: nome vazio após sanitização"
        )
    
    return safe_name


@router.get(
    "/imoveis",
    response_model=pagination_schema.PaginatedResponse[imovel_schema.ImovelOut],
    summary="Listar imóveis disponíveis",
    description="""
    Lista imóveis disponíveis com paginação e filtros.
    
    Este endpoint é público e não requer autenticação.
    Os resultados são cacheados para melhor performance.
    """,
    responses={
        200: {
            "description": "Lista de imóveis disponíveis",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "titulo": "Apartamento à beira-mar",
                                "descricao": "Apartamento com vista para o mar",
                                "metragem": 80,
                                "quartos": 2,
                                "distancia_praia": "100m",
                                "tipo_aluguel": "Diária",
                                "mobilhada": True,
                                "preco": "500.00",
                                "disponivel": True,
                                "imagens": ["/images/img1.jpg"]
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 10,
                        "total_pages": 1
                    }
                }
            }
        }
    }
)
@limiter.limit("60/minute")
def listar_imoveis(
    request: Request,
    distancia_praia: Optional[str] = Query(None, description="Filtrar por distância da praia (ex: '100m', '500m', '1km')"),
    quartos: Optional[int] = Query(None, ge=0, description="Filtrar por número mínimo de quartos"),
    tipo_aluguel: Optional[str] = Query(None, description="Filtrar por tipo de aluguel (ex: 'Diária', 'Mensal')"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(None, ge=1, le=settings.MAX_PAGE_SIZE, description="Itens por página"),
    db: Session = Depends(get_db)
):
    """Lista imóveis disponíveis com paginação e filtros"""
    if page_size is None:
        page_size = settings.DEFAULT_PAGE_SIZE
    
    imoveis, total = imovel_service.listar_imoveis_paginated(
        db=db,
        page=page,
        page_size=page_size,
        disponivel=True,
        distancia_praia=distancia_praia,
        quartos=quartos,
        tipo_aluguel=tipo_aluguel
    )
    logger.info(f"Listando imóveis disponíveis: página {page}, tamanho {page_size}, total {total}")
    
    return pagination_schema.PaginatedResponse.create(
        items=imoveis,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get(
    "/imoveis/{imovel_id}",
    response_model=imovel_schema.ImovelOut,
    summary="Obter imóvel por ID",
    description="""
    Retorna os detalhes completos de um imóvel específico.
    
    Este endpoint é público e não requer autenticação.
    """,
    responses={
        200: {
            "description": "Detalhes do imóvel",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "titulo": "Apartamento à beira-mar",
                        "descricao": "Apartamento com vista para o mar",
                        "metragem": 80,
                        "quartos": 2,
                        "distancia_praia": "100m",
                        "tipo_aluguel": "Diária",
                        "mobilhada": True,
                        "preco": "500.00",
                        "disponivel": True,
                        "imagens": ["/images/img1.jpg", "/images/img2.jpg"]
                    }
                }
            }
        },
        404: {
            "description": "Imóvel não encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Imóvel não encontrado"}
                }
            }
        }
    }
)
@limiter.limit("60/minute")
def obter_imovel(
    request: Request,
    imovel_id: int = Path(..., description="ID do imóvel", gt=0),
    db: Session = Depends(get_db)
):
    """Obtém um imóvel específico por ID"""
    try:
        imovel = imovel_service.obter_imovel_por_id(db, imovel_id)
        logger.info(f"Imóvel {imovel_id} consultado")
        return imovel
    except ValueError:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

@router.get("/imoveis_indisponiveis", response_model=pagination_schema.PaginatedResponse[imovel_schema.ImovelOut])
def listar_imoveis_indisponiveis(
    distancia_praia: Optional[str] = Query(None, description="Filtrar por distância da praia"),
    quartos: Optional[int] = Query(None, ge=0, description="Filtrar por número mínimo de quartos"),
    tipo_aluguel: Optional[str] = Query(None, description="Filtrar por tipo de aluguel"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(None, ge=1, le=settings.MAX_PAGE_SIZE, description="Itens por página"),
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_user),
):
    """Lista imóveis indisponíveis com paginação e filtros (requer autenticação)"""
    if page_size is None:
        page_size = settings.DEFAULT_PAGE_SIZE
    
    imoveis, total = imovel_service.listar_imoveis_paginated(
        db=db,
        page=page,
        page_size=page_size,
        disponivel=False,
        distancia_praia=distancia_praia,
        quartos=quartos,
        tipo_aluguel=tipo_aluguel
    )
    logger.info(f"Listando imóveis indisponíveis: página {page}, tamanho {page_size}, total {total}")
    
    return pagination_schema.PaginatedResponse.create(
        items=imoveis,
        total=total,
        page=page,
        page_size=page_size
    )

# Imóveis - criação
@router.post("/imoveis", response_model=imovel_schema.ImovelOut)
async def criar_imovel(
    imovel: imovel_schema.ImovelCreate = Depends(imovel_schema.ImovelCreate.as_form),
    imagens: List[UploadFile]     = File(...),
    db: Session                  = Depends(get_db),
    _: user_model.User               = Depends(get_current_active_user),
):
    saved_filenames: List[str] = []
    try:
        for file in imagens:
            validar_tipo(file)
            await validar_tamanho(file)
            # Valida o filename original antes de processar
            if file.filename:
                validar_filename(file.filename)
            ext = os.path.splitext(file.filename or "")[1] or ".jpg"
            unique_name = f"{uuid.uuid4().hex}{ext}"
            dest = os.path.join(IMAGES_DIR, unique_name)
            try:
                async with aiofiles.open(dest, "wb") as out:
                    content = await file.read()
                    await out.write(content)
                saved_filenames.append(unique_name)
            except (OSError, IOError) as e:
                logger.error(f"Erro ao salvar arquivo {unique_name}: {e}")
                # Limpa arquivos já salvos em caso de erro
                for fn in saved_filenames:
                    try:
                        os.remove(os.path.join(IMAGES_DIR, fn))
                    except OSError:
                        pass
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro ao salvar arquivo: {str(e)}"
                )

        im = imovel_service.criar_imovel(db, imovel, image_filenames=saved_filenames)
        return im
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar imóvel: {e}", exc_info=True)
        # Limpa arquivos salvos em caso de erro
        for fn in saved_filenames:
            try:
                os.remove(os.path.join(IMAGES_DIR, fn))
            except OSError:
                pass
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao criar imóvel"
        )

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
    try:
        if novas_imagens:
            for file in novas_imagens:
                validar_tipo(file)
                await validar_tamanho(file)
                # Valida o filename original antes de processar
                if file.filename:
                    validar_filename(file.filename)
                ext = os.path.splitext(file.filename or "")[1] or ".jpg"
                unique_name = f"{uuid.uuid4().hex}{ext}"
                dest = os.path.join(IMAGES_DIR, unique_name)
                try:
                    async with aiofiles.open(dest, "wb") as out:
                        content = await file.read()
                        await out.write(content)
                    saved_filenames.append(unique_name)
                except (OSError, IOError) as e:
                    logger.error(f"Erro ao salvar arquivo {unique_name}: {e}")
                    # Limpa arquivos já salvos em caso de erro
                    for fn in saved_filenames:
                        try:
                            os.remove(os.path.join(IMAGES_DIR, fn))
                        except OSError:
                            pass
                    raise HTTPException(
                        status_code=500,
                        detail=f"Erro ao salvar arquivo: {str(e)}"
                    )

        # 2) atualiza campos não-nulos
        update_data = imovel_in.model_dump(exclude_unset=True, exclude={"image_filenames"})
        for field, value in update_data.items():
            setattr(db_imovel, field, value)

        # 3) associa as imagens recém-salvas
        for fn in saved_filenames:
            img = imovel_model.Image(filename=fn, imovel_id=db_imovel.id)
            db.add(img)

        db.commit()
        db.refresh(db_imovel)
        return db_imovel
    except HTTPException:
        db.rollback()
        # Limpa arquivos salvos em caso de erro
        for fn in saved_filenames:
            try:
                os.remove(os.path.join(IMAGES_DIR, fn))
            except OSError:
                pass
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar imóvel: {e}", exc_info=True)
        # Limpa arquivos salvos em caso de erro
        for fn in saved_filenames:
            try:
                os.remove(os.path.join(IMAGES_DIR, fn))
            except OSError:
                pass
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao atualizar imóvel"
        )

# Upload de imagens extra
@router.post("/imoveis/{imovel_id}/images", response_model=imovel_schema.ImovelOut)
async def upload_images_para_imovel(
    imovel_id: int = Path(..., description="ID do imóvel"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_user)
):
    saved = []
    try:
        for file in files:
            validar_tipo(file)
            await validar_tamanho(file)
            # Valida o filename original antes de processar
            if file.filename:
                validar_filename(file.filename)
            ext = os.path.splitext(file.filename or "")[1] or ".jpg"
            name = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(IMAGES_DIR, name)
            try:
                async with aiofiles.open(path, "wb") as out_file:
                    content = await file.read()
                    await out_file.write(content)
                saved.append(name)
            except (OSError, IOError) as e:
                logger.error(f"Erro ao salvar arquivo {name}: {e}")
                # Limpa arquivos já salvos em caso de erro
                for fn in saved:
                    try:
                        os.remove(os.path.join(IMAGES_DIR, fn))
                    except OSError:
                        pass
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro ao salvar arquivo: {str(e)}"
                )
        return imovel_service.add_images_to_imovel(db, imovel_id, saved)
    except HTTPException:
        # Limpa arquivos salvos em caso de erro HTTP
        for fn in saved:
            try:
                os.remove(os.path.join(IMAGES_DIR, fn))
            except OSError:
                pass
        raise
    except ValueError:
        # Limpa arquivos salvos quando imóvel não é encontrado
        for fn in saved:
            try:
                os.remove(os.path.join(IMAGES_DIR, fn))
            except OSError:
                pass
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    except Exception as e:
        logger.error(f"Erro ao fazer upload de imagens: {e}", exc_info=True)
        # Limpa arquivos salvos em caso de erro
        for fn in saved:
            try:
                os.remove(os.path.join(IMAGES_DIR, fn))
            except OSError:
                pass
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao fazer upload de imagens"
        )

# Servir imagens (público - não requer autenticação)
@router.get("/images/{filename}")
@limiter.limit("120/minute")
def serve_image(
    request: Request,
    filename: str
):
    # Valida o filename para prevenir path traversal
    try:
        safe_filename = validar_filename(filename)
    except HTTPException:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")
    
    # Usa o filename validado para construir o caminho
    path = os.path.join(IMAGES_DIR, safe_filename)
    
    # Valida que o caminho final está dentro do diretório permitido (prevenção adicional)
    try:
        # Resolve o caminho absoluto e verifica se está dentro de IMAGES_DIR
        abs_path = os.path.abspath(path)
        abs_images_dir = os.path.abspath(IMAGES_DIR)
        if not abs_path.startswith(abs_images_dir):
            raise HTTPException(status_code=400, detail="Caminho de arquivo inválido")
    except (OSError, ValueError) as e:
        logger.error(f"Erro ao validar caminho do arquivo: {e}")
        raise HTTPException(status_code=400, detail="Caminho de arquivo inválido")
    
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    
    try:
        return FileResponse(path=path)
    except (OSError, IOError) as e:
        logger.error(f"Erro ao servir arquivo {filename}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao servir arquivo")


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