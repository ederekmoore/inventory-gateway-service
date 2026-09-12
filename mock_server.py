import sqlite3
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from typing import Optional

app = FastAPI(title="Mock R2 API & Cached Search Gateway", version="0.0.1")

# --- DATABASE SETUP & SEEDING ---
DB_NAME = "inventory.db"  # In-memory SQLite for high-speed local dev

def init_db():
    conn = sqlite3.connect(DB_NAME)
    
    # 1. Product catalog mock data (GET /items)
    items_data = [
        {"id": "1001", "productid": "CAM-FX6", "description": "Sony FX6 Cinema Line Camera Body", "categoryid": "CAM", "active": True, "total_stock": 12, "daily_rate": 250.00},
        {"id": "1002", "productid": "CAM-RED-V", "description": "RED V-Raptor 8K VV Camera", "categoryid": "CAM", "active": True, "total_stock": 6, "daily_rate": 500.00},
        {"id": "1003", "productid": "LGT-A600X", "description": "Aputure LS 600d Pro LED Light", "categoryid": "LGT", "active": True, "total_stock": 20, "daily_rate": 120.00},
        {"id": "1004", "productid": "AUD-SENN-G4", "description": "Sennheiser ew 112P G4 Wireless Mic Set", "categoryid": "AUD", "active": True, "total_stock": 35, "daily_rate": 45.00},
        {"id": "1005", "productid": "AUD-MIX-F8N", "description": "Zoom F8n Pro Field Recorder", "categoryid": "AUD", "active": True, "total_stock": 15, "daily_rate": 75.00},
    ]
    
    # 2. Serialized asset mock data (GET /assets)
    assets_data = [
        {"id": "A-101", "item_id": "1001", "assetid": "SN-FX6-001", "assetstatus": "In", "shelfid": "A1", "binnumber": "B12", "currentsiteid": "MAIN"},
        {"id": "A-102", "item_id": "1001", "assetid": "SN-FX6-002", "assetstatus": "Out", "shelfid": "A1", "binnumber": "B12", "currentsiteid": "MAIN"},
        {"id": "A-103", "item_id": "1003", "assetid": "SN-A600-08", "assetstatus": "In", "shelfid": "C3", "binnumber": "B04", "currentsiteid": "MAIN"},
        {"id": "A-104", "item_id": "1004", "assetid": "SN-SENN-19", "assetstatus": "Repair", "shelfid": "REP", "binnumber": "R01", "currentsiteid": "MAIN"},
    ]

    # Use Pandas to write data structures straight into SQLite
    df_items = pd.DataFrame(items_data)
    df_assets = pd.DataFrame(assets_data)

    df_items.to_sql("items", conn, if_exists="replace", index=False)
    df_assets.to_sql("assets", conn, if_exists="replace", index=False)

    # Build SQLite Full-Text Search (FTS5) table for sub-millisecond search
    cursor = conn.cursor()
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
            id UNINDEXED,
            productid,
            description,
            categoryid
        );
    """)
    cursor.execute("""
        INSERT INTO items_fts(id, productid, description, categoryid)
        SELECT id, productid, description, categoryid FROM items;
    """)
    conn.commit()
    conn.close()

# Initialize mock DB on startup
init_db()


# --- MOCK R2 API ENDPOINTS (Mimics UBS R2 API outputs) ---

@app.get("/r2/api/items", tags=["Mock R2 API"])
def get_r2_items(siteid: Optional[str] = "MAIN"):
    """Mimics R2 GET /items endpoint."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM items WHERE active = 1", conn)
    conn.close()
    return df.to_dict(orient="records")

@app.get("/r2/api/items/{item_id}", tags=["Mock R2 API"])
def get_r2_item_by_id(item_id: str, siteid: Optional[str] = "MAIN"):
    """Mimics R2 GET /items/{id}?siteid={siteid} endpoint."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM items WHERE id = ?", conn, params=(item_id,))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail="Item not found")
    return df.to_dict(orient="records")[0]

@app.get("/r2/api/assets", tags=["Mock R2 API"])
def get_r2_assets(item_id: Optional[str] = None):
    """Mimics R2 GET /assets endpoint."""
    conn = sqlite3.connect(DB_NAME)
    if item_id:
        df = pd.read_sql_query("SELECT * FROM assets WHERE item_id = ?", conn, params=(item_id,))
    else:
        df = pd.read_sql_query("SELECT * FROM assets", conn)
    conn.close()
    return df.to_dict(orient="records")


# --- CUSTOM ENHANCED SEARCH ENDPOINT (Your wrapper service) ---

@app.get("/api/v1/search", tags=["Enhanced Search Layer"])
def search_inventory(q: str = Query(..., min_length=1, description="Search term")):
    """
    High-performance custom search endpoint querying local SQLite FTS index.
    """
    conn = sqlite3.connect(DB_NAME)
    fts_query = """
        SELECT i.* 
        FROM items i
        JOIN items_fts fts ON i.id = fts.id
        WHERE items_fts MATCH ?
    """
    df_results = pd.read_sql_query(fts_query, conn, params=(f"{q}*",))
    conn.close()

    return {
        "query": q,
        "count": len(df_results),
        "results": df_results.to_dict(orient="records")
    }