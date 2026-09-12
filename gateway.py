import asyncio
import sqlite3
import httpx
import pandas as pd

from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Security, Depends, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings


#Environment Configuration
class Settings(BaseSettings):
    GATEWAY_DB_NAME: str = "search_cache.db"
    GATEWAY_API_KEY: str = "secure_client_key"
    SYNC_INTERVAL_SECONDS: int = 30
    R2_BASE_URL: str = "https://127.0.0.1:8000/r2/api"
    R2_API_KEY: str = "mock_dev_dev_api_key_12345"

    class Config:
        env_file = ".env"
settings = Settings()

#Database Cache Setup
def init_cache_db():
    """Initialize the SQLite database for caching search results."""
    conn = sqlite3.connect(settings.GATEWAY_DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_items (
            id TEXT PRIMARY KEY,
            productid TEXT,
            description TEXT,
            categoryid TEXT,
            active INTEGER,
            total_stock INTEGER,
            daily_rate REAL
        )
    """)
    cursor.execute("DROP TABLE IF EXISTS items_fts")
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
            id UNINDEXED,
            productid,
            description,
            categoryid
        )
    """)
    conn.commit()
    conn.close()

#Background Sync Task
async def fetch_and_update_cache():
    """Fetch data from R2 API and update the local cache."""
    async with httpx.AsyncClient(verify=False) as client:
        headers = {"Authorization": f"Bearer {settings.R2_API_KEY}"}
        try:
            url = f"{settings.R2_BASE_URL.rstrip('/')}/items"
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                items = response.json()
                if not items:
                    print("No items fetched from R2 API.")
                    return
                
                conn = sqlite3.connect(settings.GATEWAY_DB_NAME)
                df = pd.DataFrame(items)

                #Update the cached_items table
                df.to_sql("cached_items", conn, if_exists="replace", index=False)

                #Rebuild the FTS5 table for search
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS items_fts")
                cursor.execute("""
                    CREATE VIRTUAL TABLE items_fts USING fts5(
                        id UNINDEXED,
                        productid,
                        description,
                        categoryid
                    )
                """)
                cursor.execute("""
                    INSERT INTO items_fts(id, productid, description, categoryid)
                    SELECT id, productid, description, categoryid FROM cached_items;
                """)
                conn.commit()
                conn.close()
                print(f"Cache updated with {len(items)} items from R2 API.")
            else:
                print(f"Failed to fetch items from R2 API. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error fetching items from R2 API: {e}")

async def periodic_sync():
    """Periodically sync the cache with the R2 API."""
    while True:
        await fetch_and_update_cache()
        await asyncio.sleep(settings.SYNC_INTERVAL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize the cache and start the sync task."""
    init_cache_db()
    task = asyncio.create_task(periodic_sync())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan, title="R2 Inventory Gateway", description="Gateway service for R2 Inventory API with caching and search capabilities.", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Validates the provided API key against the configured key."""
    if api_key == settings.GATEWAY_API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key"
    )

#Custom Search Endpoint
@app.get("/api/v1/search", tags=["Custom Search"], dependencies=[Depends(verify_api_key)])
def search_inventory(q: str = Query(..., min_length=1, description="Search term"),
                     categoryid: Optional[str] = Query(None, description="Filter by category ID"),
                     limit: int = Query(20, ge=1, le=100, description="Limit number of results"),
                     offset: int = Query(0, ge=0, description="Offset for pagination")):
    """Search the cached inventory using SQLite FTS5."""
    conn = sqlite3.connect(settings.GATEWAY_DB_NAME)

    if categoryid:
        query_sql = """
            SELECT i.*
            FROM cached_items i
            JOIN items_fts fts ON i.id = fts.id
            WHERE items_fts MATCH ? AND i.categoryid = ?
            LIMIT ? OFFSET ?
        """
        params = (f"{q}*", categoryid, limit, offset)
    else:
        query_sql = """
            SELECT i.*
            FROM cached_items i
            JOIN items_fts fts ON i.id = fts.id
            WHERE items_fts MATCH ?
            LIMIT ? OFFSET ?
        """
        params = (f"{q}*", limit, offset)

    df_results = pd.read_sql_query(query_sql, conn, params=params)
    conn.close()

    return{
        "query": q,
        "category_filter": categoryid,
        "limit": limit,
        "offset": offset,
        "results_count": len(df_results),
        "results": df_results.to_dict(orient="records")
    }

#Live Asset Details Endpoint
@app.get("/api/v1/items/{item_id}/assets", tags=["Asset Details"], dependencies=[Depends(verify_api_key)])
async def get_live_assets(item_id: str):
    """Fetch live asset details for a specific item from the R2 API."""
    async with httpx.AsyncClient(verify=False) as client:
        headers = {"Authorization": f"Bearer {settings.R2_API_KEY}"}
        url = f"{settings.R2_BASE_URL.rstrip('/')}/assets"

        try:
            response = await client.get(url, headers=headers, params={"item_id": item_id}, timeout=5.0)
            if response.status_code == 200:
                return {"item_id": item_id, "assets": response.json()}
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"No assets found for item_id: {item_id}")
            else:
                raise HTTPException(status_code=500, detail="Failed to reach R2 asset service")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"R2 service unavailable: {e}")
        
            