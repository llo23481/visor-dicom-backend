from sqlalchemy.orm import Session
from models import Estudio
from schemas import EstudioCreate

def crear_estudio(db: Session, estudio: EstudioCreate):
    nuevo = Estudio(**estudio.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

def obtener_estudios(db: Session):
    return db.query(Estudio).all()
