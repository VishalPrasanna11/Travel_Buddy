from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Heroku provides DATABASE_URL; fall back to individual vars for local dev
_heroku_url = os.getenv("DATABASE_URL", "")
if _heroku_url:
    # Heroku uses postgres:// but SQLAlchemy needs postgresql://
    if _heroku_url.startswith("postgres://"):
        _heroku_url = _heroku_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif _heroku_url.startswith("postgresql://"):
        _heroku_url = _heroku_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    DATABASE_URL = _heroku_url
    DB_SSL_MODE = "require"
else:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "userapp")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_SSL_MODE = os.getenv("DB_SSL_MODE", "prefer")
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSL_MODE}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": DB_SSL_MODE
    } if DB_SSL_MODE else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency function to get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()