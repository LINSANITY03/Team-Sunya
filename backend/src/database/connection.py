
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base


# --------------------------------------------------
# Database configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "recommendations.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


# --------------------------------------------------
# SQLAlchemy engine
# --------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    echo=False,
)


# Enable SQLite foreign-key enforcement.
@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# --------------------------------------------------
# Database session
# --------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# --------------------------------------------------
# Database initialization
# --------------------------------------------------

def init_db() -> None:
    """Create database tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# FastAPI database dependency
# --------------------------------------------------

def get_db():
    """
    Provide a database session to FastAPI endpoints.

    Automatically closes the session after the request.
    """
    db: Session = SessionLocal()

    try:
        yield db
    finally:
        db.close()
