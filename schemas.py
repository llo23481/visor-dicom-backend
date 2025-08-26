# schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ImagenOut(BaseModel):
    id: int
    sop_instance_uid: Optional[str] = None
    instance_number: Optional[int] = None
    is_multiframe: bool
    num_frames: int
    archivo: str

    class Config:
        orm_mode = True

class SerieOut(BaseModel):
    id: int
    series_instance_uid: Optional[str] = None
    modality: Optional[str] = None
    series_description: Optional[str] = None
    body_part: Optional[str] = None
    medico_remitente: Optional[str] = None
    num_imagenes: int

    class Config:
        orm_mode = True

class SerieDetail(SerieOut):
    imagenes: List[ImagenOut]

class EstudioOut(BaseModel):
    id: int
    study_instance_uid: Optional[str] = None
    nombre: Optional[str] = None
    paciente_id: Optional[str] = None
    nacimiento: Optional[str] = None
    descripcion: Optional[str] = None
    fecha: Optional[str] = None
    institucion: Optional[str] = None
    estado: str
    num_series: int
    num_imagenes: int
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class EstudioDetail(EstudioOut):
    series: List[SerieOut]

class UploadResult(BaseModel):
    estudio_id: int
    series_creadas: int
    imagenes_creadas: int
