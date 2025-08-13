from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from contextlib import contextmanager


DB_PATH = os.environ.get(
    "BOOKMARK_DB",
    os.path.join(os.path.dirname(__file__), "..", "bookmarks.sqlite3"),
)
DB_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_session():
    """FastAPI dependency that yields a DB session and handles commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


