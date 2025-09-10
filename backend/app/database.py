from sqlmodel import SQLModel, create_engine, Session
from .config import get_settings


settings = get_settings()
engine = create_engine(f"sqlite:///{settings.SQLITE_PATH}", echo=settings.DEBUG, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        yield session

