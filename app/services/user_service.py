from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models  import user_model
from app.schemas import user_schema

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str):
    return db.query(user_model.User).filter(user_model.User.username == username).first()


def create_user(db: Session, user_in: user_schema.UserCreate):
    hashed_password = pwd_context.hash(user_in.password)
    db_user = user_model.User(
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


def delete_user(db: Session, user_id: int) -> None:
    db_user = db.query(user_model.User).get(user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False