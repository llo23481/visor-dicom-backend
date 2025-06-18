from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import pydicom  # ⬅️ Importante para leer archivos DICOM
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

    # Guardar el archivo
    with open(ruta, "wb") as f:
        f.write(await file.read())

    # Leer metadatos del archivo DICOM
    try:
        ds = pydicom.dcmread(ruta)
        nombre = str(ds.get("PatientName", "Desconocido"))
        fecha = str(ds.get("StudyDate", "00000000"))
        nacimiento = str(ds.get("PatientBirthDate", "00000000"))
        descripcion = str(ds.get("StudyDescription", "Sin descripción"))
        paciente_id = str(ds.get("PatientID", "000000"))
        institucion = str(ds.get("InstitutionName", "Desconocida"))
    except:
        nombre = "Desconocido"
        fecha = "00000000"
        nacimiento = "00000000"
        descripcion = "Sin descripción"
        paciente_id = "000000"
        institucion = "Desconocida"

    nuevo_estudio = schemas.EstudioCreate(
        nombre=nombre,
        fecha=fecha,
        nacimiento=nacimiento,
        descripcion=descripcion,
        paciente_id=paciente_id,
        institucion=institucion,
        archivo=file.filename
    )
    return crud.crear_estudio(db, nuevo_estudio)

@app.get("/estudios", response_model=list[schemas.EstudioOut])
def listar_estudios(db: Session = Depends(get_db)):
    return crud.obtener_estudios(db)