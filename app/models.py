from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Imovel(Base):
    __tablename__ = "imoveis"

    id               = Column(Integer, primary_key=True, index=True)
    titulo           = Column(String, nullable=False)
    descricao        = Column(String, nullable=False)
    metragem         = Column(Integer, nullable=False)
    quartos          = Column(Integer, nullable=False)
    distancia_praia  = Column(String, nullable=False)
    tipo_aluguel     = Column(String, nullable=False)
    mobilhada        = Column(Boolean, nullable=False)
    preco            = Column(String, nullable=False)    # <-- novo campo
    images           = relationship(
        "Image",
        back_populates="imovel",
        cascade="all, delete-orphan"
    )
class Image(Base):
    __tablename__ = "images"

    id        = Column(Integer, primary_key=True, index=True)
    filename  = Column(String, unique=True, nullable=False, index=True)
    imovel_id = Column(Integer, ForeignKey("imoveis.id", ondelete="CASCADE"))
    imovel    = relationship("Imovel", back_populates="images")

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String, unique=True, index=True, nullable=False)
    full_name       = Column(String, nullable=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    disabled        = Column(Boolean, default=False)
    is_admin        = Column(Boolean, default=False)