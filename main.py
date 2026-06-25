import re
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ── in-memory state ──────────────────────────────────────────────────────────
documents: dict[int, str] = {}
index: dict[str, set[int]] = defaultdict(set)
next_id = 1
remove_stops = True

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "it",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "and",
    "or",
    "not",
    "this",
    "that",
    "was",
    "are",
    "be",
    "has",
    "had",
    "with",
    "as",
    "by",
    "from",
    "but",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z]+", text.lower())
    if remove_stops:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens


def rebuild_index():
    global index
    index = defaultdict(set)
    for doc_id, text in documents.items():
        for token in tokenize(text):
            index[token].add(doc_id)


def all_ids() -> set[int]:
    return set(documents.keys())


# ── boolean parser ────────────────────────────────────────────────────────────
class Parser:
    def __init__(self, query: str):
        self.tokens = re.findall(r"[A-Za-z]+|\(|\)", query)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def parse(self) -> set[int]:
        return self.parse_or()

    def parse_or(self) -> set[int]:
        left = self.parse_and()
        while self.peek() and self.peek().upper() == "OR":
            self.consume()
            left = left | self.parse_and()
        return left

    def parse_and(self) -> set[int]:
        left = self.parse_not()
        while self.peek() and self.peek().upper() == "AND":
            self.consume()
            left = left & self.parse_not()
        return left

    def parse_not(self) -> set[int]:
        if self.peek() and self.peek().upper() == "NOT":
            self.consume()
            return all_ids() - self.parse_not()
        return self.parse_primary()

    def parse_primary(self) -> set[int]:
        t = self.peek()
        if t is None:
            return set()
        if t == "(":
            self.consume()
            result = self.parse_or()
            if self.peek() == ")":
                self.consume()
            return result
        if t.upper() not in ("AND", "OR", "NOT"):
            self.consume()
            return index.get(t.lower(), set()).copy()
        return set()


def boolean_search(query: str) -> set[int]:
    return Parser(query).parse()


# ── pydantic models ───────────────────────────────────────────────────────────
class DocBody(BaseModel):
    text: str


class QueryBody(BaseModel):
    query: str


# ── routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/add")
async def add_doc(body: DocBody):
    global next_id
    text = body.text.strip()
    if not text:
        return {"error": "empty document"}
    doc_id = next_id
    documents[doc_id] = text
    next_id += 1
    for token in tokenize(text):
        index[token].add(doc_id)
    return {"id": doc_id, "total": len(documents), "terms": len(index)}


@app.get("/api/docs")
async def list_docs():
    docs = [{"id": i, "preview": t[:80]} for i, t in documents.items()]
    return {"docs": docs, "total": len(documents), "terms": len(index)}


@app.post("/api/search")
async def search(body: QueryBody):
    q = body.query.strip()
    if not q:
        return {"error": "empty query"}
    try:
        ids = boolean_search(q)
    except Exception as e:
        return {"error": str(e)}
    results = [{"id": i, "text": documents[i]} for i in sorted(ids)]
    return {"results": results, "count": len(results)}


@app.delete("/api/docs")
async def clear_docs():
    global next_id
    documents.clear()
    index.clear()
    next_id = 1
    return {"ok": True}


@app.patch("/api/stops")
async def toggle_stops(body: dict):
    global remove_stops
    remove_stops = bool(body.get("enabled", True))
    rebuild_index()
    return {"remove_stops": remove_stops, "terms": len(index)}
