# main.py
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import os
import uuid

from database import SessionLocal, engine, Base
from models import Product

# ==========================
# Criar tabelas se não existirem
# ==========================
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TenisX API",
    description="API para gerenciar produtos da loja TenisX",
    version="1.0.0",
)

# ==========================
# CORS
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção, ajuste para seu domínio real
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# STATIC FILES (IMAGENS)
# ==========================
STATIC_DIR = "static"
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Servir a pasta /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Base dir do projeto (para localizar index.html, admin.html, etc.)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==========================
# PÁGINA INICIAL (FRONT)
# ==========================
@app.get("/", response_class=FileResponse)
def read_root():
    """
    Serve o arquivo index.html na raiz do site.
    """
    index_path = os.path.join(BASE_DIR, "index.html")
    return FileResponse(index_path)


# Se quiser expor outras páginas HTML direto (opcional):
@app.get("/admin", response_class=FileResponse)
def admin_page():
    admin_path = os.path.join(BASE_DIR, "admin.html")
    return FileResponse(admin_path)


@app.get("/vendedor", response_class=FileResponse)
def vendedor_page():
    vendedor_path = os.path.join(BASE_DIR, "vendedor.html")
    return FileResponse(vendedor_path)


# ==========================
# DEPENDÊNCIA DO BANCO
# ==========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================
# SCHEMAS Pydantic
# ==========================
class ProductBase(BaseModel):
    name: str
    brand: str
    gender: Optional[str] = None
    category: Optional[str] = None
    price: float
    sizes: str                   # Ex: "37,38,39,40"
    status: str = "ativo"
    image_url: Optional[str] = None
    description: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ==========================
# ROTAS DE PRODUTO (API)
# ==========================
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
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
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
    return {"detail": "Produto deletado"}


# ==========================
# UPLOAD DE IMAGEM
# ==========================
@app.post("/upload-image")
async def upload_image(request: Request, file: UploadFile = File(...)):
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


# ==========================
# RODAR LOCALMENTE (DEV)
# ==========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
