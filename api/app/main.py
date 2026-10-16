from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="SpectraMeet API")


@app.get("/api/ping")
def ping() -> dict:
    return {"ok": True, "mock_pipeline": settings.use_mock_pipeline}


if __name__ == "__main__":
    # Jalankan dengan: python -m app.main  (port mengikuti API_PORT di .env)
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.api_port, reload=True)
