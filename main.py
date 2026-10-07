import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.database import engine, Base
from app.routers import agent, execution, finops, auth, inquiries, managed, knowledge


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-generate DB schema tables on startup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Warning: Exception during schema creation: {e}")
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(agent.router, prefix=settings.API_V1_PREFIX)
app.include_router(execution.router, prefix=settings.API_V1_PREFIX)
app.include_router(finops.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(inquiries.router, prefix=settings.API_V1_PREFIX)
app.include_router(managed.router, prefix=settings.API_V1_PREFIX)
app.include_router(knowledge.router, prefix=settings.API_V1_PREFIX)

@app.get("/healthz", tags=["System Health"])
async def health_check():
    return {"status": "HEALTHY", "engine": settings.PROJECT_NAME}

# Mount static files directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "app", "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve UI at root URL
@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Static frontend not found. Place index.html inside app/static/"}

@app.get("/studio", include_in_schema=False)
async def serve_studio():
    studio_file = os.path.join(STATIC_DIR, "studio.html")
    if os.path.exists(studio_file):
        return FileResponse(studio_file)
    return {"message": "Studio frontend not found. Place studio.html inside app/static/"}

@app.get("/auth", include_in_schema=False)
async def serve_auth():
    auth_file = os.path.join(STATIC_DIR, "auth.html")
    if os.path.exists(auth_file):
        return FileResponse(auth_file)
    return {"message": "Auth frontend not found. Place auth.html inside app/static/"}

@app.get("/chat/{agent_id}", include_in_schema=False)
async def serve_chat_portal(agent_id: str):
    chat_file = os.path.join(STATIC_DIR, "chat.html")
    if os.path.exists(chat_file):
        return FileResponse(chat_file)
    return {"message": "Chat portal frontend not found. Place chat.html inside app/static/"}