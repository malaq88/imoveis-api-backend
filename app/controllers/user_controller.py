from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.core.config import settings
from app.models import user_model
from passlib.context import CryptContext
from app.schemas import user_schema
from app.services import user_service
from sqlalchemy.orm import Session
from app.core.dependencies import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY, authenticate_user, get_db, get_current_active_user, get_current_active_admin # type: ignore
from jose import jwt

router = APIRouter(
    prefix="",
    tags=["Usuários"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Token
@router.post("/token", response_model=user_schema.Token)
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
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": user.username, "exp": datetime.utcnow() + expires},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Usuários
@router.post("/users/", response_model=user_schema.UserOut)
def create_user(
    user_in: user_schema.UserCreate,
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_admin)
):
    if user_service.get_user_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    return user_service.create_user(db, user_in)

@router.get("/users/", response_model=list[user_schema.UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: user_model.User = Depends(get_current_active_admin)
):
    query = db.query(user_model.User).all()
    if not query:
        raise HTTPException(status_code=404, detail="No users found")
    return query

@router.get("/users/me", response_model=user_schema.UserOut)
def read_users_me(
    current_user: user_model.User = Depends(get_current_active_user)
):
    return current_user

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_active_admin)]
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    if not user_service.delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)