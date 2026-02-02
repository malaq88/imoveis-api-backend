from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base

class Imovel(Base):
    __tablename__ = "imoveis"

    id               = Column(Integer, primary_key=True, index=True)
    titulo           = Column(String, nullable=False)
    descricao        = Column(String, nullable=False)
    metragem         = Column(Integer, nullable=False)
    quartos          = Column(Integer, nullable=False, index=True)
    distancia_praia  = Column(String, nullable=False, index=True)
    tipo_aluguel     = Column(String, nullable=False, index=True)
    mobilhada        = Column(Boolean, nullable=False)
    preco            = Column(String, nullable=False)
    disponivel       = Column(Boolean, default=True, nullable=False, index=True)
    
    # Índice composto para consultas comuns (disponivel + filtros)
    __table_args__ = (
        Index('idx_disponivel_quartos', 'disponivel', 'quartos'),
        Index('idx_disponivel_distancia', 'disponivel', 'distancia_praia'),
        Index('idx_disponivel_tipo', 'disponivel', 'tipo_aluguel'),
    )
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
