# Inventory Gateway Service

A high-performance gateway service for inventory management with advanced search capabilities, caching, and live asset tracking.

## Overview

The **Inventory Gateway Service** acts as a middleware layer between client applications and inventory backend systems (R2 API). It provides:

- **Lightning-fast search** using SQLite FTS5 (Full-Text Search)
- **Intelligent caching** with automatic synchronization
- **Live asset tracking** for real-time item details
- **API key authentication** for secure access
- **CORS support** for cross-origin requests
- **Comprehensive testing** suite

## Features

### 🔍 Advanced Search
- Full-text search powered by SQLite FTS5
- Optional category filtering
- Configurable pagination (limit/offset)
- Sub-millisecond response times

### 💾 Smart Caching
- Automatic synchronization with upstream R2 API
- Configurable sync intervals (default: 30 seconds)
- SQLite-backed persistent cache
- Minimal network overhead

### 🏷️ Live Asset Details
- Fetch real-time asset information for inventory items
- Per-item asset tracking and status
- Shelf and bin location data
- Site location information

### 🔐 Security
- API key-based authentication (via `X-API-Key` header)
- Environment-based configuration
- Secure credential management

## Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd inventory-gateway-service
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** (optional)
   
   Create a `.env` file in the project root:
   ```env
   GATEWAY_DB_NAME=search_cache.db
   GATEWAY_API_KEY=your_secure_api_key
   SYNC_INTERVAL_SECONDS=30
   R2_BASE_URL=https://your-r2-api.com
   R2_API_KEY=your_r2_api_key
   ```

### Running the Service

**Start the gateway service:**
```bash
uvicorn gateway:app --host 0.0.0.0 --port 8001 --reload
```

**Start the mock R2 API** (for development/testing):
```bash
uvicorn mock_server:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at `http://localhost:8001`

## API Endpoints

### Search Inventory

**Endpoint:** `GET /api/v1/search`

**Authentication:** Required (X-API-Key header)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | ✓ | Search term (min 1 character) |
| `categoryid` | string | - | Filter results by category ID |
| `limit` | integer | - | Number of results (1-100, default: 20) |
| `offset` | integer | - | Pagination offset (default: 0) |

**Example Request:**
```bash
curl -X GET "http://localhost:8001/api/v1/search?q=camera&categoryid=CAM&limit=10" \
  -H "X-API-Key: secure_client_key"
```

**Response:**
```json
{
  "query": "camera",
  "category_filter": "CAM",
  "limit": 10,
  "offset": 0,
  "results_count": 2,
  "results": [
    {
      "id": "1001",
      "productid": "CAM-FX6",
      "description": "Sony FX6 Cinema Line Camera Body",
      "categoryid": "CAM",
      "active": 1,
      "total_stock": 12,
      "daily_rate": 250.0
    }
  ]
}
```

### Get Live Asset Details

**Endpoint:** `GET /api/v1/items/{item_id}/assets`

**Authentication:** Required (X-API-Key header)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `item_id` | string | The ID of the item to fetch assets for |

**Example Request:**
```bash
curl -X GET "http://localhost:8001/api/v1/items/1001/assets" \
  -H "X-API-Key: secure_client_key"
```

**Response:**
```json
{
  "item_id": "1001",
  "assets": [
    {
      "id": "A-101",
      "item_id": "1001",
      "assetid": "SN-FX6-001",
      "assetstatus": "In",
      "shelfid": "A1",
      "binnumber": "B12",
      "currentsiteid": "MAIN"
    }
  ]
}
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GATEWAY_DB_NAME` | string | `search_cache.db` | SQLite database filename |
| `GATEWAY_API_KEY` | string | `secure_client_key` | API key for authentication |
| `SYNC_INTERVAL_SECONDS` | int | `30` | Cache sync interval in seconds |
| `R2_BASE_URL` | string | `https://127.0.0.1:8000/r2/api` | Base URL for R2 API |
| `R2_API_KEY` | string | `mock_dev_dev_api_key_12345` | API key for R2 service |

## Project Structure

```
inventory-gateway-service/
├── gateway.py              # Main gateway service (FastAPI app)
├── mock_server.py          # Mock R2 API server (for development)
├── test_gateway.py         # Unit and integration tests
├── requirements.txt        # Python dependencies
├── .env                    # Environment configuration (optional)
└── README.md              # This file
```

### Key Files

- **`gateway.py`** - Main gateway application with:
  - Cache database initialization
  - Background sync task
  - FastAPI application setup
  - Search and asset endpoints
  - Authentication middleware

- **`mock_server.py`** - Development mock server featuring:
  - Sample inventory data (cameras, lights, audio equipment)
  - Mock R2 API endpoints
  - SQLite FTS5 indexed search

- **`test_gateway.py`** - Comprehensive test suite covering:
  - Authentication (valid/invalid API keys)
  - Search functionality with filters
  - Live asset endpoint

## Testing

Run the test suite with pytest:

```bash
pytest test_gateway.py -v
```

**Test Coverage:**
- ✓ API key authentication
- ✓ Search with category filters
- ✓ Pagination and limits
- ✓ Live asset endpoint
- ✓ Error handling (404, 500, 503)

## Technical Stack

| Component | Technology |
|-----------|------------|
| **Web Framework** | FastAPI |
| **Server** | Uvicorn (ASGI) |
| **Database** | SQLite with FTS5 |
| **Data Processing** | Pandas |
| **HTTP Client** | httpx |
| **Testing** | pytest |
| **Configuration** | Pydantic Settings |

## Performance

- **Search Response Time:** Sub-millisecond (SQLite FTS5)
- **Cache Sync:** Configurable interval (default 30s)
- **Concurrent Requests:** Async-first design
- **Database:** SQLite with full-text search indexes

## Development

### Local Development Setup

1. Install dependencies with dev tools:
   ```bash
   pip install -r requirements.txt
   ```

2. Start both services:
   ```bash
   # Terminal 1: Mock R2 API
   uvicorn mock_server:app --port 8000 --reload
   
   # Terminal 2: Gateway Service
   uvicorn gateway:app --port 8001 --reload
   ```

3. Access the interactive API docs:
   - Gateway: http://localhost:8001/docs
   - Mock Server: http://localhost:8000/docs

### Making Changes

The `--reload` flag auto-reloads the server on file changes. Simply edit files and save!

## Error Handling

The service returns appropriate HTTP status codes:

| Status | Scenario |
|--------|----------|
| `200` | Successful request |
| `401` | Missing or invalid API key |
| `404` | Resource not found (e.g., no assets for item) |
| `500` | Internal server error |
| `503` | Upstream R2 service unavailable |

## License

This project is provided as-is for inventory management purposes.

## Support

For issues, feature requests, or questions, please open an issue in the repository.
