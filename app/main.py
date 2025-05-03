import os
import uuid
from typing import Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import aiofiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import crud, schemas, models
from app.settings import settings
from app.database import SessionLocal, engine, Base

# Configurações carregadas do .env
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Cria tabelas no banco
Base.metadata.create_all(bind=engine)

# Lifespan handler para startup e shutdown
defining_lifespan = asynccontextmanager(
    lambda app: __import__('builtins')
)
# Correção: descriptor asynccontextmanager wrapper
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed admin
    db = SessionLocal()
    try:
        if not crud.get_user_by_username(db, settings.ADMIN_USERNAME):
            admin_in = schemas.UserCreate(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                full_name="Administrador",
                password=settings.ADMIN_PASSWORD,
                is_admin=True
            )
            crud.create_user(db, admin_in)
    finally:
        db.close()
    yield
    # Shutdown: (opcional)
    
# Cria a aplicação FastAPI com lifespan
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependência para sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funções de autenticação e autorização
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_user(db: Session, username: str, password: str):
    user = crud.get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_admin(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

# Diretório para armazenar imagens
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

def validar_tipo(file: UploadFile):
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Apenas JPEG ou PNG são aceitos")

# Endpoint de autenticação
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": user.username, "exp": datetime.utcnow() + access_token_expires},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoints de usuário
@app.post("/users/", response_model=schemas.UserOut)
def create_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_active_admin)
):
    if crud.get_user_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db, user_in)

@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(
    current_user: models.User = Depends(get_current_active_user)
):
    return current_user

# Endpoints de imóveis
@app.get("/imoveis", response_model=List[schemas.ImovelOut])
def listar_imoveis(
    distancia_praia: Optional[str] = None,
    quartos: Optional[int] = None,
    tipo_aluguel: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Imovel)
    if distancia_praia:
        query = query.filter(models.Imovel.distancia_praia == distancia_praia)
    if quartos is not None:
        query = query.filter(models.Imovel.quartos == quartos)
    if tipo_aluguel:
        query = query.filter(models.Imovel.tipo_aluguel == tipo_aluguel)
    return query.all()

@app.post("/imoveis", response_model=schemas.ImovelOut)
async def criar_imovel(
    imovel: schemas.ImovelCreate = Depends(schemas.ImovelCreate.as_form),
    imagens: List[UploadFile]     = File(...),
    db: Session                  = Depends(get_db),
    _: models.User               = Depends(get_current_active_user),
):
    # 1) salva cada UploadFile em disco e coleta filename gerado
    saved_filenames: List[str] = []
    for file in imagens:
        validar_tipo(file)
        ext = os.path.splitext(file.filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(IMAGES_DIR, unique_name)
        async with aiofiles.open(dest, "wb") as out:
            await out.write(await file.read())
        saved_filenames.append(unique_name)

    # 2) cria o imovel no banco, passando também as imagens
    im = crud.criar_imovel(db, imovel, image_filenames=saved_filenames)
    return im

@app.put("/imoveis/{imovel_id}", response_model=schemas.ImovelOut)
def update_imovel(
    imovel_id: int,
    imovel_in: schemas.ImovelCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_active_admin)
):
    db_imovel = db.query(models.Imovel).filter(models.Imovel.id == imovel_id).first()
    if not db_imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    for field, value in imovel_in.dict(exclude={"image_filenames"}).items():
        setattr(db_imovel, field, value)
    if imovel_in.image_filenames:
        existing = [img.filename for img in db_imovel.images]
        for fname in existing:
            if fname not in imovel_in.image_filenames:
                path = os.path.join(IMAGES_DIR, fname)
                if os.path.isfile(path):
                    os.remove(path)
                img_obj = next(i for i in db_imovel.images if i.filename == fname)
                db.delete(img_obj)
        for fname in imovel_in.image_filenames:
            if fname not in existing:
                db.add(models.Image(filename=fname, imovel_id=db_imovel.id))
    db.commit()
    db.refresh(db_imovel)
    return db_imovel

# Endpoints de upload de imagens
@app.post("/imoveis/{imovel_id}/images", response_model=schemas.ImovelOut)
async def upload_images_para_imovel(
    imovel_id: int = Path(..., description="ID do imóvel"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_active_admin)
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
        return crud.add_images_to_imovel(db, imovel_id, saved)
    except ValueError:
        for fn in saved:
            os.remove(os.path.join(IMAGES_DIR, fn))
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

# Endpoint para servir imagens
@app.get("/images/{filename}")
def serve_image(
    filename: str,
    _: models.User = Depends(get_current_active_admin)
):
    path = os.path.join(IMAGES_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return FileResponse(path=path)
