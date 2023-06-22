from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URL = "sqlite:///./sql_app.db"  # "postgresql://user:password@postgresserver/db"

# connect_args on SQLiteä varten, ei muuten tarvetta: https://fastapi.tiangolo.com/tutorial/sql-databases/#note <-- JATKA ABOUT TUOSTA
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
