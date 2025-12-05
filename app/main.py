from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import routes
from prometheus_client import make_asgi_app

app = FastAPI(
    title="Robot Brain Microservice",
    description="Low-latency AI microservice with tool usage and streaming.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Routes
app.include_router(routes.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    # Initialize resources (Redis, etc.)
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # Cleanup resources
    pass

@app.get("/")
async def root():
    return {
        "message": "Robot Brain Microservice",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
