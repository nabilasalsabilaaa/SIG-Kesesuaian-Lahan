from fastapi import FastAPI
from fastapi.responses import JSONResponse
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

app.include_router(layers.router,      prefix="/api", tags=["Layers"])
app.include_router(suitability.router, prefix="/api", tags=["Suitability"])
app.include_router(analyze.router,     prefix="/api", tags=["Analyze"])
app.include_router(rekomendasi.router, prefix="/api", tags=["Rekomendasi"])

# Suppress Chrome DevTools 404 errors
@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
def devtools_json():
    return JSONResponse(content={})


@app.get("/", tags=["Root"])
def root():
    return {
        "status": "ok",
        "pesan":  "SIG Kesesuaian Lahan API berjalan",
        "docs":   "/docs"
    }