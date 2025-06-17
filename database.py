from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://visor_dicom_db_user:5YAnZHOEfMQQYXfL8qHnCdQTs69Qi1Gm@dpg-d18r0o15pdvs73cs2b50-a.oregon-postgres.render.com/visor_dicom_db?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()