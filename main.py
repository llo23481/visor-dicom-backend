from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
import os, io, base64, zipfile
import numpy as np
from PIL import Image
import pydicom
from pydicom import dcmread
from pydicom.dataset import FileDataset
from database import SessionLocal, engine
import models, schemas, crud

# Crear todas las tablas antes de iniciar la app
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DICOMTROL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

UPLOAD_FOLDER = "subidos"
EXPORT_FOLDER = "exports"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

# utils
def safe_get(ds: FileDataset, key: str, default=None):
    try:
        return ds.get(key, default)
    except Exception:
        return default

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def dicom_to_pil(ds: FileDataset, frame_index: int = 0) -> Image.Image:
    try:
        # Multi-frame handling
        if hasattr(ds, "NumberOfFrames") and ds.NumberOfFrames and int(ds.NumberOfFrames) > 1:
            arr = ds.pixel_array[int(frame_index)]
        else:
            arr = ds.pixel_array

        arr = arr.astype(np.float32)

        slope = float(getattr(ds, "RescaleSlope", 1.0) or 1.0)
        intercept = float(getattr(ds, "RescaleIntercept", 0.0) or 0.0)
        arr = arr * slope + intercept

        # windowing if available
        wc = safe_get(ds, "WindowCenter")
        ww = safe_get(ds, "WindowWidth")
        if isinstance(wc, (list, tuple)): wc = float(wc[0])
        if isinstance(ww, (list, tuple)): ww = float(ww[0])

        if wc is not None and ww:
            low = wc - ww/2
            high = wc + ww/2
            arr = np.clip(arr, low, high)
        else:
            low, high = np.percentile(arr, (1, 99))
            arr = np.clip(arr, low, high)

        arr = (arr - arr.min()) / (arr.max() - arr.min() + 1e-6)
        arr = (arr * 255.0).astype(np.uint8)

        photometric = str(getattr(ds, "PhotometricInterpretation", "")).upper()
        if "MONOCHROME1" in photometric:
            arr = 255 - arr

        img = Image.fromarray(arr)
        return img
    except Exception as e:
        arr = getattr(ds, "pixel_array", None)
        if arr is None:
            raise e
        arr = arr.astype(np.float32)
        arr = (arr - arr.min()) / (arr.max() - arr.min() + 1e-6)
        arr = (arr * 255.0).astype(np.uint8)
        return Image.fromarray(arr)

# upload single
@app.post("/subir", response_model=schemas.UploadResult)
async def subir_uno(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _process_files([file], db)

# upload multiple
@app.post("/subir-multiples", response_model=schemas.UploadResult)
async def subir_multiples(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    return await _process_files(files, db)

async def _process_files(files: list[UploadFile], db: Session) -> schemas.UploadResult:
    series_creadas = 0
    imagenes_creadas = 0
    estudio_id_final = None

    for up in files:
        contenido = await up.read()
        tmp_path = os.path.join(UPLOAD_FOLDER, f"__tmp__{up.filename}")
        with open(tmp_path, "wb") as f:
            f.write(contenido)

        try:
            ds: FileDataset = dcmread(tmp_path, force=True)

            study_uid = str(safe_get(ds, "StudyInstanceUID", "") or "")
            series_uid = str(safe_get(ds, "SeriesInstanceUID", "") or "")
            sop_uid = str(safe_get(ds, "SOPInstanceUID", "") or "")
            modality = str(safe_get(ds, "Modality", "") or "")
            series_desc = str(safe_get(ds, "SeriesDescription", "") or "")
            body_part = str(safe_get(ds, "BodyPartExamined", "") or "")
            medico = str(safe_get(ds, "ReferringPhysicianName", "") or "")

            # --- Nacimiento en formato DD-MM-YYYY ---
            raw_birth = str(safe_get(ds, "PatientBirthDate", "") or "")
            nacimiento_fmt = ""
            if len(raw_birth) == 8:  # YYYYMMDD
                nacimiento_fmt = f"{raw_birth[6:8]}-{raw_birth[4:6]}-{raw_birth[0:4]}"

            est_defaults = dict(
                nombre=str(safe_get(ds, "PatientName", "") or ""),
                paciente_id=str(safe_get(ds, "PatientID", "") or ""),
                nacimiento=nacimiento_fmt,
                descripcion=str(safe_get(ds, "StudyDescription", "") or ""),
                fecha=str(safe_get(ds, "StudyDate", "") or ""),
                institucion=str(safe_get(ds, "InstitutionName", "") or ""),
            )
            est = crud.get_or_create_estudio(db, study_uid or None, est_defaults)

            ser_defaults = dict(
                modality=modality,
                series_description=series_desc,
                body_part=body_part,
                medico_remitente=medico,
            )
            ser = crud.get_or_create_serie(db, est.id, series_uid or None, ser_defaults)

            nframes = int(getattr(ds, "NumberOfFrames", 1) or 1)
            is_multiframe = nframes > 1

            study_dir = os.path.join(UPLOAD_FOLDER, study_uid or f"study_{est.id}")
            series_dir = os.path.join(study_dir, series_uid or f"series_{ser.id}")
            ensure_dir(series_dir)

            final_path = os.path.join(series_dir, up.filename)
            with open(final_path, "wb") as f:
                f.write(contenido)

            # --- generar preview PNG (miniatura) y guardarla en DB ---
            try:
                preview_img = dicom_to_pil(ds, frame_index=0)
                preview_img.thumbnail((240, 240), Image.LANCZOS)
                buf = io.BytesIO()
                preview_img.save(buf, format="PNG")
                preview_bytes = buf.getvalue()
            except Exception:
                preview_bytes = None

            img = crud.add_imagen(
                db=db,
                serie_id=ser.id,
                sop_uid=sop_uid or None,
                instance_number=int(getattr(ds, "InstanceNumber", 0) or 0),
                is_multiframe=is_multiframe,
                num_frames=nframes,
                archivo=up.filename,
                ruta=os.path.relpath(final_path, start="."),
                preview_bytes=preview_bytes
            )

            ser.num_imagenes = (ser.num_imagenes or 0) + 1
            estudio_id_final = est.id
            imagenes_creadas += 1

        except Exception:
            pass
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass

    if estudio_id_final is None:
        raise HTTPException(status_code=400, detail="No se pudo procesar ningún DICOM válido.")

    crud.recalc_counts_for_estudio(db, estudio_id_final)
    db.commit()
    series_creadas = len(crud.listar_series_de_estudio(db, estudio_id_final))
    return schemas.UploadResult(estudio_id=estudio_id_final, series_creadas=series_creadas, imagenes_creadas=imagenes_creadas)

# list studies
@app.get("/estudios", response_model=list[schemas.EstudioOut])
def listar_estudios(db: Session = Depends(get_db)):
    return crud.listar_estudios(db)

@app.get("/estudios/{estudio_id}", response_model=schemas.EstudioDetail)
def obtener_detalles_estudio(estudio_id: int, db: Session = Depends(get_db)):
    est = crud.obtener_estudio(db, estudio_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    _ = est.series
    return est

@app.get("/estudios/{estudio_id}/series", response_model=list[schemas.SerieOut])
def listar_series(estudio_id: int, db: Session = Depends(get_db)):
    est = crud.obtener_estudio(db, estudio_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    return crud.listar_series_de_estudio(db, estudio_id)

@app.get("/series/{serie_id}", response_model=schemas.SerieDetail)
def obtener_detalle_serie(serie_id: int, db: Session = Depends(get_db)):
    s = crud.obtener_serie(db, serie_id)
    if not s:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    _ = s.imagenes
    return s

@app.get("/series/{serie_id}/imagenes", response_model=list[schemas.ImagenOut])
def listar_imagenes(serie_id: int, db: Session = Depends(get_db)):
    s = crud.obtener_serie(db, serie_id)
    if not s:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    imagenes = crud.listar_imagenes_de_serie(db, serie_id)
    out = []
    for img in imagenes:
        preview_b64 = None
        if img.imagen_preview:
            try:
                preview_b64 = base64.b64encode(img.imagen_preview).decode("utf-8")
            except Exception:
                preview_b64 = None
        out.append({
            "id": img.id,
            "sop_instance_uid": img.sop_instance_uid,
            "instance_number": img.instance_number,
            "is_multiframe": img.is_multiframe,
            "num_frames": img.num_frames,
            "archivo": img.archivo,
            "preview_base64": preview_b64
        })
    return out

@app.put("/estudios/{estudio_id}/visto", response_model=schemas.EstudioOut)
def marcar_visto(estudio_id: int, db: Session = Depends(get_db)):
    est = crud.marcar_estudio_visto(db, estudio_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    db.commit()
    return est

@app.get("/imagen/{imagen_id}")
def obtener_imagen(imagen_id: int, frame: int = Query(0, ge=0), db: Session = Depends(get_db)):
    img = db.query(models.Imagen).filter(models.Imagen.id == imagen_id).one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    ruta = img.ruta
    if ruta and os.path.isfile(ruta):
        try:
            ds = dcmread(ruta, force=True)
            total_frames = int(getattr(ds, "NumberOfFrames", 1) or 1)
            fidx = max(0, min(frame, total_frames - 1))
            im = dicom_to_pil(ds, frame_index=fidx)
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            buf.seek(0)
            return StreamingResponse(buf, media_type="image/png")
        except Exception:
            pass

    if img.imagen_preview:
        return StreamingResponse(io.BytesIO(img.imagen_preview), media_type="image/png")

    raise HTTPException(status_code=404, detail="Archivo/preview no disponible")

# --- NUEVO ENDPOINT EXPORTAR ---
@app.get("/exportar")
def exportar():
    """
    Genera un ZIP de exportación (ejemplo).
    Más adelante aquí se conectará la lógica real de exportar estudios.
    """
    zip_path = os.path.join(EXPORT_FOLDER, "dicomtrol_export.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.writestr("informe.txt", "Exportación generada desde DICOMTROL ✅")
        zipf.writestr("datos.json", '{"paciente": "John Doe", "ID": "12345"}')

    return FileResponse(
        path=zip_path,
        filename="dicomtrol_export.zip",
        media_type="application/zip"
    )

# --- Render puerto dinámico ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
