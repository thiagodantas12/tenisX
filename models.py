# models.py
from sqlalchemy import Column, Integer, String, Float, Text
from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)          # Nome do produto
    brand = Column(String(100), nullable=False)         # Marca
    gender = Column(String(50), nullable=True)          # Masculino / Feminino / Unissex
    category = Column(String(100), nullable=True)       # Casual / Corrida / etc
    price = Column(Float, nullable=False)               # Preço
    sizes = Column(String(200), nullable=False)         # Ex.: "37,38,39,40"
    status = Column(String(50), nullable=False, default="ativo")
    image_url = Column(String(500), nullable=True)      # URL da imagem
    description = Column(Text, nullable=True)           # Descrição do produto
