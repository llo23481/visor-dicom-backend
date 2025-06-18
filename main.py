from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from database import SessionLocal, engine
import crud, models, schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 👇 Permitir peticiones desde cualquier origen (Frontend en Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

UPLOAD_FOLDER = "subidos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/subir", response_model=schemas.EstudioOut)
async def subir_archivo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ruta = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(ruta, "wb") as f:
        f.write(await file.read())

    nuevo_estudio = schemas.EstudioCreate(
        nombre="Desconocido",
        fecha="00000000",
        nacimiento="00000000",
        descripcion="Sin descripción",
        paciente_id="000000",
        institucion="Desconocida",
        archivo=file.filename
    )
    return crud.crear_estudio(db, nuevo_estudio)

@app.get("/estudios", response_model=list[schemas.EstudioOut])
def listar_estudios(db: Session = Depends(get_db)):
    return crud.obtener_estudios(db)