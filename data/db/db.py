"""Describes the database operations with sqlalchemy"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./bajeti.db"  # file-based SQLite
# SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:" #memory based

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Returns the database for Dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
