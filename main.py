# main.py
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import os
import uuid

from database import SessionLocal, engine, Base
from models import Product

# Cria as tabelas no banco, se ainda não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TenisX API",
    description="API para gerenciar produtos da loja TenisX",
    version="1.0.0",
)

# ========= CORS =========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção, coloque o domínio da sua loja
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= ARQUIVOS ESTÁTICOS (IMAGENS) =========
STATIC_DIR = "static"
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# /static/... vai servir arquivos dessa pasta
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ========= DEPENDÊNCIA DE DB =========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========= Pydantic Schemas =========
class ProductBase(BaseModel):
    name: str
    brand: str
    gender: Optional[str] = None
    category: Optional[str] = None
    price: float
    sizes: str                   # "37,38,39,40"
    status: str = "ativo"
    image_url: Optional[str] = None
    description: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int

    # Pydantic v2: substitui orm_mode=True
    model_config = ConfigDict(from_attributes=True)


# ========= ROTAS DE PRODUTOS =========
@app.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return products


@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**product_in.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    for field, value in product_in.dict().items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    db.delete(product)
    db.commit()
    return


# ========= UPLOAD DE IMAGEM =========
@app.post("/upload-image")
async def upload_image(request: Request, file: UploadFile = File(...)):
    """
    Recebe uma imagem e salva em static/uploads.
    Retorna a URL pública para ser usada como image_url.
    """
    original_name = file.filename
    ext = os.path.splitext(original_name)[1].lower()

    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(
            status_code=400,
            detail="Formato de imagem não suportado. Use JPG, JPEG, PNG ou WEBP.",
        )

    new_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, new_name)

    with open(save_path, "wb") as f:
        f.write(await file.read())

    base_url = str(request.base_url).rstrip("/")
    url = f"{base_url}/static/uploads/{new_name}"

    return {"url": url}
