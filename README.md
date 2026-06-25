# Simple Search Engine

A small FastAPI app for adding documents and running Boolean search queries.

## Features
- add documents through the web UI
- search with `AND`, `OR`, `NOT`, and parentheses
- toggle stop-word removal
- keep everything in memory for simple testing

## Run
```bash
uvicorn main:app --reload
```

Then open:
- `http://127.0.0.1:8000`

## Install
```bash
pip install -r requirements.txt
```

## API
- `POST /api/add` — add a document
- `GET /api/docs` — list documents
- `POST /api/search` — search documents
- `DELETE /api/docs` — clear documents
- `PATCH /api/stops` — toggle stop-word removal

## Notes
- The data stays in memory.
- Restarting the app clears all documents.
