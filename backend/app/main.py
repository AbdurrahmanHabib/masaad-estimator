import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from contextlib import asynccontextmanager
# Note: In production, ensure app.core.config is set up
# from app.core.config import settings

# Database Connection Pool Setup
class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        # Prioritize Railway/Production DATABASE_URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            database_url = "postgresql://user:pass@localhost/masaad"
            
        # Railway URLs often start with postgres://, but asyncpg needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        self.pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=5,
            max_size=20
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

db = Database()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB Pool
    await db.connect()
    yield
    # Shutdown: Clean up
    await db.disconnect()

app = FastAPI(
    title="Masaad Estimator API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware (configured for Next.js frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "active", "region": "me-south-1"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)