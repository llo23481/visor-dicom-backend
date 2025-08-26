# crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import models

# ===== Estudio =====
def get_or_create_estudio(db: Session, study_uid: Optional[str], defaults: dict) -> models.Estudio:
    est = None
    if study_uid:
        est = db.query(models.Estudio).filter(models.Estudio.study_instance_uid == study_uid).one_or_none()
    if est:
        # rellenar campos vacíos si vienen defaults
        for k, v in defaults.items():
            if getattr(est, k, None) in (None, "", 0) and v not in (None, "", 0):
                setattr(est, k, v)
        return est
    est = models.Estudio(study_instance_uid=study_uid, **defaults)
    db.add(est)
    db.flush()
    return est

def listar_estudios(db: Session):
    return db.query(models.Estudio).order_by(models.Estudio.created_at.desc()).all()

def obtener_estudio(db: Session, estudio_id: int) -> Optional[models.Estudio]:
    return db.query(models.Estudio).filter(models.Estudio.id == estudio_id).one_or_none()


# ===== Serie =====
def get_or_create_serie(db: Session, estudio_id: int, series_uid: Optional[str], defaults: dict) -> models.Serie:
    ser = None
    if series_uid:
        ser = db.query(models.Serie).filter(
            models.Serie.estudio_id == estudio_id,
            models.Serie.series_instance_uid == series_uid
        ).one_or_none()
    if ser:
        for k, v in defaults.items():
            if getattr(ser, k, None) in (None, "", 0) and v not in (None, "", 0):
                setattr(ser, k, v)
        return ser
    ser = models.Serie(estudio_id=estudio_id, series_instance_uid=series_uid, **defaults)
    db.add(ser)
    db.flush()
    return ser

def listar_series_de_estudio(db: Session, estudio_id: int):
    return db.query(models.Serie).filter(models.Serie.estudio_id == estudio_id).all()

def obtener_serie(db: Session, serie_id: int) -> Optional[models.Serie]:
    return db.query(models.Serie).filter(models.Serie.id == serie_id).one_or_none()


# ===== Imagen =====
def add_imagen(db: Session, serie_id: int, sop_uid: Optional[str], instance_number: Optional[int],
               is_multiframe: bool, num_frames: int, archivo: str, ruta: str) -> models.Imagen:
    # evitar duplicados por SOP UID
    img = None
    if sop_uid:
        img = db.query(models.Imagen).filter(
            models.Imagen.serie_id == serie_id,
            models.Imagen.sop_instance_uid == sop_uid
        ).one_or_none()
    if img:
        return img
    img = models.Imagen(
        serie_id=serie_id,
        sop_instance_uid=sop_uid,
        instance_number=instance_number,
        is_multiframe=is_multiframe,
        num_frames=num_frames,
        archivo=archivo,
        ruta=ruta
    )
    db.add(img)
    db.flush()
    return img

def listar_imagenes_de_serie(db: Session, serie_id: int):
    return db.query(models.Imagen).filter(models.Imagen.serie_id == serie_id).order_by(
        models.Imagen.instance_number.asc().nullsfirst()
    ).all()


# ===== Utilitarios =====
def recalc_counts_for_estudio(db: Session, estudio_id: int):
    num_series = db.query(func.count(models.Serie.id)).filter(models.Serie.estudio_id == estudio_id).scalar() or 0
    num_imagenes = db.query(func.count(models.Imagen.id)).join(
        models.Serie, models.Imagen.serie_id == models.Serie.id
    ).filter(models.Serie.estudio_id == estudio_id).scalar() or 0
    est = db.query(models.Estudio).get(estudio_id)
    if est:
        est.num_series = num_series
        est.num_imagenes = num_imagenes
        db.flush()

def marcar_estudio_visto(db: Session, estudio_id: int) -> Optional[models.Estudio]:
    est = obtener_estudio(db, estudio_id)
    if not est:
        return None
    est.estado = "Visto"
    db.flush()
    return est
