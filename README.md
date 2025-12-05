# Robot Brain Microservice

A production-ready, low-latency "robot brain" microservice in Python that uses Gemini API for natural language + function-calling and integrates external tools.

## Features

- **Gemini Integration**: Streaming chat with function calling.
- **Tools**: Weather, News, Web Search, School Info, Developer Info, Device Control.
- **Caching**: Redis with in-memory fallback.
- **Observability**: Prometheus metrics.
- **Safety**: Device control requires admin confirmation.

## Quickstart

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- API Keys (Gemini, OpenWeatherMap, NewsAPI, Google Search)

### Setup

1.  **Clone the repository** (if applicable).
2.  **Configure Keys**:
    Edit `config.md` in the root directory and add your API keys.
    *Note: Do not commit `config.md` with real keys.*

3.  **Run Locally**:
    ```bash
    # Create venv
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Run Redis (optional, falls back to in-memory)
    # docker run -p 6379:6379 redis:alpine
    
    # Run App
    uvicorn app.main:app --reload
    ```

4.  **Run with Docker Compose**:
    ```bash
    cd docker
    docker-compose up --build
    ```

## API Usage

### Chat Endpoint

`POST /api/v1/chat`

```json
{
  "message": "What is the weather in London?",
  "history": []
}
```

Returns a Server-Sent Events (SSE) stream.

### Admin Confirmation

`POST /api/v1/admin/confirm?request_id=...&admin_token=...`

## Testing

Run unit and integration tests:
```bash
pytest
```

Run performance test:
```bash
python tests/performance_test.py
```
