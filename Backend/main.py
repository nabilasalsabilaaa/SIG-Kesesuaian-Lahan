from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import layers, suitability, analyze, rekomendasi

app = FastAPI(
    title="SIG Kesesuaian Lahan — Jambu Mete",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(layers.router,      tags=["Layers"])
app.include_router(suitability.router, tags=["Suitability"])
app.include_router(analyze.router,     tags=["Analyze"])
app.include_router(rekomendasi.router, tags=["Rekomendasi"])


@app.get("/", tags=["Root"])
def root():
    return {
        "status": "ok",
        "pesan":  "SIG Kesesuaian Lahan API berjalan",
        "docs":   "/docs"
    }