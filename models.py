# models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Estudio(Base):
    __tablename__ = "estudios"
    id = Column(Integer, primary_key=True, index=True)

    study_instance_uid = Column(String, unique=True, index=True, nullable=True)

    nombre = Column(String, nullable=True)
    paciente_id = Column(String, nullable=True)
    nacimiento = Column(String, nullable=True)
    descripcion = Column(String, nullable=True)
    fecha = Column(String, nullable=True)
    institucion = Column(String, nullable=True)

    estado = Column(String, default="Pendiente")
    num_series = Column(Integer, default=0)
    num_imagenes = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación con series
    series = relationship("Serie", back_populates="estudio", cascade="all, delete-orphan")


class Serie(Base):
    __tablename__ = "series"
    id = Column(Integer, primary_key=True, index=True)

    estudio_id = Column(Integer, ForeignKey("estudios.id", ondelete="CASCADE"), nullable=False)
    series_instance_uid = Column(String, index=True, nullable=True)
    modality = Column(String, nullable=True)
    series_description = Column(String, nullable=True)
    body_part = Column(String, nullable=True)
    medico_remitente = Column(String, nullable=True)

    num_imagenes = Column(Integer, default=0)

    estudio = relationship("Estudio", back_populates="series")
    imagenes = relationship("Imagen", back_populates="serie", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("estudio_id", "series_instance_uid", name="uix_estudio_series_uid"),
    )


class Imagen(Base):
    __tablename__ = "imagenes"
    id = Column(Integer, primary_key=True, index=True)

    serie_id = Column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=False)

    sop_instance_uid = Column(String, index=True, nullable=True)
    instance_number = Column(Integer, nullable=True)

    is_multiframe = Column(Boolean, default=False)
    num_frames = Column(Integer, default=1)

    archivo = Column(String, nullable=False)  # nombre de archivo
    ruta = Column(String, nullable=False)     # ruta relativa al archivo guardado

    serie = relationship("Serie", back_populates="imagenes")

    __table_args__ = (
        UniqueConstraint("serie_id", "sop_instance_uid", name="uix_serie_sop_uid"),
    )
