# 🧠 Knowledge Hub for AI Agents in SDLC

> **Trung tâm quản lý tri thức** (Long-term Memory & Context Provider) cho các AI Agent tham gia vào chu kỳ phát triển phần mềm.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Vector_DB-Qdrant-red)](https://qdrant.tech)
[![Neo4j](https://img.shields.io/badge/Graph_DB-Neo4j-008CC1?logo=neo4j)](https://neo4j.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 📌 Tổng quan

**Knowledge Hub** là một dịch vụ độc lập (microservice) cung cấp API cho AI Agent (lập trình, kiểm thử, viết tài liệu) truy xuất ngữ cảnh chính xác từ codebase và tài liệu dự án.

### Vấn đề giải quyết

| Vấn đề | Giải pháp |
|--------|-----------|
| LLM context window giới hạn — không thể đọc cả codebase | Retrieval chính xác đúng đoạn code/tài liệu cần thiết |
| Tìm kiếm từ khóa bỏ sót quan hệ ngữ nghĩa; vector search bỏ sót quan hệ cấu trúc | **Hybrid Retrieval** = Semantic Search + Graph Expansion |
| AI Agent nhận context lỗi thời khi code thay đổi | Sync & Eviction tự động, hard delete ngay lập tức |
| Tri thức phân tán ở nhiều nguồn (code, docs, commits) | Một điểm truy xuất duy nhất qua REST API |

### Kiến trúc tổng quan

```
Source Code / Markdown / PDF / Git Log / SRS
              │
              ▼
     ┌─────────────────┐
     │ Language Parser │  ← parse 1 lần → Intermediate Representation (IR)
     └────────┬────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
  Chunk & Embed   Entity & Relationship
       │             │
       ▼             ▼
  [Qdrant]       [Neo4j]
  Vector DB      Graph DB
       │             │
       └──────┬──────┘
              ▼
      Hybrid Retrieval
      (0.7 × vector + 0.3 × graph)
              │
              ▼
       REST API (FastAPI)
              │
              ▼
          AI Agent
```

---

## 🚀 Quick Start

### Yêu cầu

- Docker & Docker Compose
- Python 3.11+ (chỉ cần nếu chạy dev local)

### Khởi động hệ thống

```bash
# 1. Clone và cấu hình
git clone <repo-url>
cd knowledge-hub
cp .env.example .env

# 2. Khởi động toàn bộ hệ thống (API + Qdrant + Neo4j)
docker compose up -d

# 3. Kiểm tra health
curl http://localhost:8000/health

# 4. Nạp dữ liệu mẫu lần đầu
python scripts/seed_data.py

# 5. Chạy demo end-to-end
python scripts/demo_flow.py --skip-seed

# 6. Mở demo UI
# http://localhost:3000
```

### Gọi thử API đầu tiên

```bash
# Ingest một file source code
curl -X POST http://localhost:8000/ingest \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"sources": [{"type": "directory", "path": "./app", "include_patterns": ["*.py"]}]}'

# Query ngữ cảnh bằng ngôn ngữ tự nhiên
curl -X POST http://localhost:8000/query \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does authentication work in the movies API?", "top_k": 5}'
```

---

## ⚙️ Cấu hình môi trường

Tạo file `.env` từ `.env.example`:

| Biến | Mặc định | Mô tả |
|------|---------|-------|
| `API_KEY` | `dev-secret-key` | API key (comma-separated cho nhiều key) |
| `EMBEDDING_PROVIDER` | `openai` | `openai` mặc định; `local` chỉ dùng khi cài thêm `sentence-transformers` |
| `OPENAI_API_KEY` | _(trống)_ | Bắt buộc nếu `EMBEDDING_PROVIDER=openai` |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model embedding OpenAI; chọn `text-embedding-3-small` để tiết kiệm chi phí |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant Vector DB URL |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `password` | Neo4j password |
| `MAX_GRAPH_HOPS` | `2` | Số hop tối đa khi Graph Expansion |
| `GIT_POLL_INTERVAL_SEC` | `60` | Interval polling Git log (giây) |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## 📡 API Reference

### POST `/ingest` — Ingest dữ liệu

```json
// Request
{
  "sources": [
    {"type": "file", "path": "app/services/auth.py"},
    {"type": "directory", "path": "app/", "include_patterns": ["*.py", "*.md"]},
    {"type": "git_repo", "path": "/path/to/repo", "branch": "main", "include_git_log": true}
  ]
}

// Response 202 Accepted
{"job_id": "3f8a1c2d-...", "status": "accepted", "estimated_files": 28}
```

### GET `/ingest/{job_id}` — Theo dõi trạng thái ingest

```json
// Response 200 OK
{
  "job_id": "3f8a1c2d-...",
  "status": "completed",
  "files_processed": 28,
  "chunks_created": 156,
  "nodes_created": 87
}
```

### POST `/query` — Truy vấn ngữ cảnh (endpoint chính)

```json
// Request
{
  "query": "How does the movies API authenticate users?",
  "top_k": 5,
  "options": {
    "enable_graph_expansion": true,
    "max_hops": 2
  }
}

// Response 200 OK
{
  "results": [
    {
      "chunk_id": "a1b2c3d4-...",
      "content": "async def get_movie(..., user: UserSchema = Depends(get_current_user)):\n    ...",
      "relevance_score": 0.89,
      "metadata": {
        "source_file": "app/routers/movies.py",
        "entity_name": "get_movie",
        "line_start": 81,
        "line_end": 88,
        "language": "python"
      },
      "graph_context": [
        {"entity": "get_current_user", "file": "app/services/auth.py", "relationship": "CALLS", "hop": 1}
      ]
    }
  ],
  "total_results": 5,
  "latency_ms": {"vector_search": 45, "graph_expansion": 120, "total": 189}
}
```

### POST `/sync` — Trigger cập nhật tri thức

```json
// Request
{"scope": "all"}   // hoặc {"scope": "file", "path": "app/services/auth.py"}

// Response 202 Accepted
{"job_id": "7d9e2f3a-...", "status": "accepted"}
```

### GET `/health` — Health check

```json
// Response 200 OK
{
  "status": "ok",
  "services": {
    "vector_db": {"status": "ok", "total_chunks": 156},
    "graph_db": {"status": "ok", "total_nodes": 87}
  }
}
```

---

## 🏗️ Cấu trúc dự án

```
knowledge-hub/
├── app/
│   ├── api/              # M6: API Gateway (FastAPI)
│   │   ├── routers/      #   ingest, query, sync, health
│   │   ├── middleware/   #   auth, rate_limit
│   │   └── schemas/      #   Pydantic request/response models
│   ├── parser/           # M1: Language Parser (Python AST, Markdown, PDF, Git)
│   ├── embedding/        # M2: Chunker + Embedding (local / OpenAI)
│   ├── graph/            # M3: Entity & Relationship Extraction
│   ├── retrieval/        # M4: Hybrid Retrieval (vector + graph)
│   ├── sync/             # M5: Sync & Eviction (watchdog + git polling)
│   └── storage/          #     VectorStore & GraphStore interfaces + implementations
├── tests/
│   ├── unit/             # Unit tests per module (coverage ≥ 70%)
│   └── integration/      # End-to-end flow tests (cần DB)
├── scripts/
│   ├── seed_data.py      # Nạp dữ liệu mẫu lần đầu
│   └── healthcheck.py    # Kiểm tra health sau docker compose up
├── .project-docs/        # Tài liệu thiết kế (SRS, Design, ADR, Module Spec)
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 🔧 Tech Stack

| Thành phần | Công nghệ | Lý do chọn |
|-----------|----------|-----------|
| API Framework | FastAPI | Async, Pydantic validation, auto OpenAPI docs |
| Vector DB | Qdrant | Docker single-node nhẹ, payload filter tốt cho sync |
| Graph DB | Neo4j Community | Cypher support, multi-hop traversal, community lớn |
| Embedding (default) | OpenAI `text-embedding-3-small` | Rẻ, nhẹ, chất lượng đủ tốt cho MVP |
| Embedding (optional) | `all-MiniLM-L6-v2` | Chỉ dùng nếu cài thêm `sentence-transformers` và bật `EMBEDDING_PROVIDER=local` |
| Code Parser (Python) | `ast` (stdlib) | Built-in, ổn định |
| Code Parser (Java/C#) | `tree-sitter` | Universal parser, nhiều ngôn ngữ |
| Doc Parser | `markdown-it-py`, `pypdf` | |
| Git Parser | `gitpython` | |
| File Watcher | `watchdog` | Cross-platform file system events |
| Rate Limiting | `slowapi` | SlowAPI tích hợp native với FastAPI |

---

## 📊 Hybrid Retrieval — Cách hoạt động

```
Query: "How does movies API authenticate users?"
         │
         ▼
  1. Vector Search (Qdrant)
     → top-10 chunk gần nghĩa nhất (cosine similarity ≥ 0.5)
     → Tìm được: get_movie(), get_current_user()
         │
         ▼
  2. Graph Expansion (Neo4j, max 2 hop)
     → MATCH (n)-[:CALLS|IMPLEMENTS|DESCRIBES*1..2]->(m)
     → Tìm thêm: AuthService.authenticate(), AuthDataManager.get_user()
         │
         ▼
  3. Score Fusion
     → final_score = 0.7 × vector_score + 0.3 × graph_score
     → Deduplicate, sort DESC
         │
         ▼
  4. Context Builder
     → Trim theo token limit (8,000 token)
     → Ưu tiên: code_function > doc_section > git_log
```

**Kết quả:** AI Agent nhận được ngữ cảnh về `get_movie()` VÀ `get_current_user()` từ domain `auth` — mà thuần vector search sẽ bỏ sót cross-domain dependency này.

---

## 📁 Tài liệu thiết kế

Tất cả tài liệu kỹ thuật nằm trong `.project-docs/`:

| File | Nội dung |
|------|---------|
| [01-srs.md](.project-docs/01-srs.md) | Software Requirements Specification |
| [02-design.md](.project-docs/02-design.md) | Architecture Design (schema, API, data flows) |
| [03-open-questions.md](.project-docs/03-open-questions.md) | Quyết định kỹ thuật đã freeze |
| [03.5-adr.md](.project-docs/03.5-adr.md) | Architecture Decision Records (9 ADR) |
| [04-module-spec-coding-rules.md](.project-docs/04-module-spec-coding-rules.md) | Module interfaces + Coding Rules |

---

## 🧪 Chạy tests

```bash
# Unit tests (không cần Docker)
pytest tests/unit/ -v --cov=app --cov-report=term-missing

# Integration tests (cần docker compose up trước)
docker compose up -d qdrant neo4j
pytest tests/integration/ -v

# Test bằng Docker, không phụ thuộc virtualenv local
docker compose up -d --build
docker compose exec -T api pytest -q
```

## 📈 Đánh giá retrieval

```bash
# Seed dữ liệu trước khi đánh giá
python scripts/seed_data.py --path app

# Đo Recall@5 và MRR
python scripts/evaluate_retrieval.py --path tests/fixtures/eval_queries.json --threshold 0.35

# Demo flow đầy đủ: health, seed, sample query, evaluation
python scripts/demo_flow.py
```

## 🖥️ Frontend Demo UI

```bash
docker compose up -d --build
```

Mở `http://localhost:3000` để dùng giao diện chatbot:

- hỏi codebase bằng ngôn ngữ tự nhiên
- xem tool card `hybrid_retrieval` với Input/Output
- xem bảng top results gồm file, entity, score, line range và graph context
- click một result để mở drawer xem full code chunk
- bấm `Ingest` để nạp lại source path như `app`

Frontend chỉ dùng `API_KEY` để gọi backend. `OPENAI_API_KEY` vẫn nằm trong backend `.env`, không được đưa lên browser.

---

## 📝 License

MIT License — xem [LICENSE](LICENSE) để biết chi tiết.
