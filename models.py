from sqlalchemy import Column, Integer, String
from database import Base

class Estudio(Base):
    __tablename__ = "estudios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    fecha = Column(String)
    nacimiento = Column(String)
    descripcion = Column(String)
    paciente_id = Column(String)
    institucion = Column(String)
    archivo = Column(String)
