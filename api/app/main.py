from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import init_db
from app.routes import router
from app.runner import runner


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    runner.fail_orphans()
    yield
    runner.shutdown()


app = FastAPI(title="SpectraMeet API", lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    # Jalankan dengan: python -m app.main  (port mengikuti API_PORT di .env)
    import uvicorn

    # reload=False: proses pipeline adalah anak API; muat ulang otomatis akan membunuhnya di tengah jalan.
    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.api_port, reload=False)
