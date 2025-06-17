from pydantic import BaseModel

class EstudioCreate(BaseModel):
    nombre: str
    fecha: str
    nacimiento: str
    descripcion: str
    paciente_id: str
    institucion: str
    archivo: str

class EstudioOut(EstudioCreate):
    id: int

    class Config:
        orm_mode = True
