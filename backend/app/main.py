import os
import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("masaad-api")

# Database Connection Pool Setup
class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            database_url = "postgresql://user:pass@localhost/masaad"
            logger.warning("DATABASE_URL not found, defaulting to localhost")
            
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        # Retry logic: attempt to connect 5 times before failing
        for i in range(5):
            try:
                logger.info(f"Attempting to connect to database (Attempt {i+1}/5)...")
                self.pool = await asyncpg.create_pool(
                    dsn=database_url,
                    min_size=5,
                    max_size=20
                )
                logger.info("Database connection established successfully.")
                return
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                if i < 4:
                    wait_time = 2 ** i
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.critical("Could not connect to database after 5 attempts.")
                    raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed.")

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "active", "db_connected": db.pool is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)