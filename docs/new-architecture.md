# 💡 EcoStance RAG Capabilities 
### System Capabilities Summary (Text Box for Slide)
* 📥 Multi-Format Ingestion (PDF, DOCX, Excel, CSV, SQL, HTML, JSONL, TXT, MD)
* 🧩 Intelligent Chunking (sentence-aware + 10–20% overlap)
* 🔍 Hybrid Retrieval (Qdrant ANN + metadata filtering)
* 🧠 Stateful Chat (chat history, follow-ups, context tracking)
* 🗂️ File-Level Management (delete/reindex individual files)
* ⚙️ Background Processing (non-blocking, job IDs, progress tracking)
* 🧾 Transparent Sourcing (source filename, table, extraction method)
* 🚀 Scalable (clean async pipeline, cleanup service, health checks)


## High-Level End-to-End RAG Architecture
```mermaid
flowchart TD
    A["📂 Upload Documents\n(PDF, Excel, SQL, etc.)"] --> B["⚙️ Background Processing\nExtract → Clean → Chunk → Embed"]
    B --> C["🗃️ Knowledge Base\n(Qdrant Vector DB)"]
    C --> D["💬 Chat Interface\n(Streamlit UI)"]
    D --> E["🧠 Query Engine\n(Retrieve + LLM Reasoning)"]
    E --> F["✅ Answer + Sources"]
    
%%    classDef stage fill:#f0f7ff,stroke:#4a90e2,stroke-width:2px;
%%    classDef system fill:#e8f5e9,stroke:#4caf50;
    class A,B,D,E,F stage
    class C system
```
##  Document Ingestion Pipeline (Processing Stages)
```mermaid
flowchart LR
    subgraph Ingestion["📥 Ingest & Index"]
        A["📥 Upload\n(e.g., Excel, PDF, SQL)"] --> B["🧹 Clean & Normalize"]
        B --> C["🧩 Chunk\n(Semantic + Overlap)"]
        C --> D["🔖 Enrich Metadata\n(Source, Page, Timestamp, Hash)"]
        D --> E["🧠 Embed\n(all-MiniLM-L6-v2)"]
        E --> F["🚀 Upload to Qdrant\n(Collection-specific)"]
    end
    
%%    style Ingestion fill:#fafafa,stroke:#666,stroke-dasharray: 5 5
```

## Query & Response Workflow (Stateful RAG)
```mermaid
sequenceDiagram
    participant User as 🧑 User (UI)
    participant UI as 💻 Streamlit UI
    participant API as 🌐 FastAPI Backend
    participant Qdrant as 🗃️ Qdrant
    participant LLM as 🤖 Gemini LLM

    User->>UI: "What’s the price of Margherita Pizza?"
    UI->>API: POST /query\n(collection=ecostance-demo2)
    API->>Qdrant: Retrieve top-3 relevant chunks
    Qdrant-->>API: Context: {“name”: “Margherita Pizza”, “price”: “9.99”…}
    API->>LLM: “Based on this context… what’s the price?”
    LLM-->>API: “The price of Margherita Pizza is 9.99.”
    API-->>UI: { answer }
    UI-->>User: ✅ “The price of Margherita Pizza is 9.99.”
```

## System Architecture (with Tech Stack)

```mermaid

flowchart TD
  subgraph Ingest["📥 Ingestion & Indexing (Background Jobs)"]
    U["User uploads file / DB dump<br/>(via FastAPI + Uvicorn)"] --> EX["Extraction Service<br/>(PyMuPDF, Pandas, BeautifulSoup, SQL Parser)"]
    EX --> CL["Cleaning & Enrichment<br/>(spaCy, Regex, custom preprocessors)"]
    CL --> CH["Chunking Service<br/>(LangChain text splitter + metadata tagging)"]
    CH --> EMB["Embedding Service<br/>(OpenAI / Gemini / SentenceTransformers)"]
    EMB --> VDB["Qdrant Vector DB<br/>(HTTP/gRPC API)"]
    VDB -->|metadata| META["Provenance Metadata Store<br/>(JSON + SQLite / PostgreSQL)"]
  end

  subgraph API["🧠 FastAPI Backend (app/main.py)"]
    Q["User / Chat UI (React / Streamlit / REST client)"] --> ROUTER["FastAPI Router<br/>(/upload, /query, /status)"]
    ROUTER --> RET["Retriever Service<br/>(LangChain Retriever + FAISS/Qdrant client)"]
    RET --> RER["Reranker / Filter<br/>(BM25, cosine sim, optional LLM ranking)"]
    RER --> LLM["LLM / ReAct Agent<br/>(OpenAI GPT-4 / Gemini Pro via API)"]
    LLM --> RESP["Response Generator<br/>(Answer synthesis + source citations)"]
  end


  VDB --> RET
  API --> JOB
  JOB -.-> METRICS
  API -. logs .-> LOGS
  

```

## Ingestion & Background Processing 

```mermaid
sequenceDiagram
  participant UI as UI / Upload
  participant API as FastAPI / upload router
  participant JOB as Job Tracker
  participant WORK as Processing Worker(s)
  participant EX as Extraction Service
  participant CL as Cleaning Service
  participant CH as Chunking Service
  participant EMB as Embedding Service
  participant QDR as Qdrant (Vector DB)
  UI->>API: POST /api/v1/upload (file)
  API->>JOB: create job_id, store metadata
  API-->>UI: 202 Accepted (job_id, status_url)
  Note over WORK,JOB: Background workers poll / are triggered
  WORK->>JOB: claim job_id
  WORK->>EX: extract content (pdf/xlsx/sql/html)
  EX->>CL: raw -> cleaned/enriched blocks
  CL->>CH: chunk text
  CH->>EMB: create embeddings
  EMB->>QDR: upload vectors + metadata
  QDR-->>JOB: update status (completed / failed)
  JOB-->>UI: progress updates via status_url

```

## Query / Retrieval Pipeline (LLM + RAG Stack)

```mermaid
flowchart LR
  USER["User / Chat UI<br/>(React Widget / Streamlit Chat)"] --> API["FastAPI /query endpoint"]
  API --> RET["Retriever Service<br/>(LangChain + QdrantClient)"]
  RET --> CHK["Context Builder<br/>(Top-K chunks + metadata)"]
  CHK --> PROMPT["Prompt Template Engine<br/>(LangChain / custom Jinja)"]
  PROMPT --> LLM["LLM Backend<br/>(OpenAI GPT-4 / Gemini Pro)"]
  LLM --> PARSER["Response Post-Processor<br/>(Markdown parser + citation linker)"]
  PARSER --> RESP["Response + Sources<br/>(JSON / Chat format)"]
  RESP --> USER
  style LLM fill:#fef3c7,stroke:#d6b11b

```

