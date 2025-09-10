import orjson
import logging
import sys
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .database import init_db
from .api import router


def orjson_dumps(v, *, default):
    return orjson.dumps(v, default=default).decode()


app = FastAPI(default_response_class=ORJSONResponse, title="Simhastha Samwad")

load_dotenv()
settings = get_settings()

# Basic logging setup (to stdout for systemd/journald)
_logger = logging.getLogger("simhastha")
if not _logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
