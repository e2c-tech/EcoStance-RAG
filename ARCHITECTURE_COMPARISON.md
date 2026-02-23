# EcoStance RAG Architecture Comparison

This document outlines the architecture for managing high-compute AI models (BGE-M3) while maintaining high application availability.

---

## Architecture 1: Standard (1 Worker + Thread Offloading)
*Current setup implemented in the codebase.*

### Overview
A single Uvicorn process handles both the API requests and the background processing. CPU-bound tasks (Embedding, PDF Extraction) are offloaded to a **managed threadpool** using `anyio.to_thread`.

### Implementation Details
- **Workers**: 1 Uvicorn Worker.
- **Model Loading**: BGE-M3 is loaded once into the main process RAM (~2GB).
- **Concurrency**: `anyio.to_thread.run_sync` prevents CPU math from blocking the FastAPI event loop.
- **State**: Uses the PostgreSQL `background_jobs` table for persistent tracking.

### Pros & Cons
| Pros | Cons |
| :--- | :--- |
| Simple setup; no extra dependencies (like Redis). | **Scaling Limit**: Total throughput is limited by a single Python process. |
| Lowest RAM usage (~2.5GB total). | **Event Loop Risk**: If too many threads are spawned, OS context switching can still slow down responses. |
| Fast local communication. | **Risk of 504**: High CPU saturation can still cause the entire process to drop requests. |

---

## Architecture 2: Scalable (4 Workers + Dedicated Embedding Service)
*Recommended for High Traffic / Production.*

### Overview
Separates the **Web Server** from the **AI Engine**. The API workers become "stateless" (they don't load the models), and a dedicated service handles all vectorization.

### Implementation Details
- **API Workers**: 4 Uvicorn Workers. **Crucially, model loading is disabled inside these workers.**
- **Embedding Service**: 1 single process (FastAPI or Celery) that owns the BGE-M3 model.
- **Message Broker**: Redis handles communication between the 4 API workers and the 1 Embedding Service.
- **Workflow**:
    1. User uploads file.
    2. API Worker saves file and writes "PENDING" to DB.
    3. API Worker pushes task to Redis.
    4. Dedicated Embedding Worker pulls from Redis, generates vectors, and uploads to Qdrant.

### Pros & Cons
| Pros | Cons |
| :--- | :--- |
| **Zero RAM Duplication**: Each API worker uses < 100MB RAM. | Higher Complexity: Needs Redis + separate worker management. |
| **Maximum Responsiveness**: API workers stay 100% free to handle UI/UX while the model grinds away. | **Network Overhead**: Data (text) must be sent to the worker via Redis/HTTP. |
| **Fault Tolerance**: If the model crashes, the web server stays UP and provides status updates. | Higher initial setup time. |

---

## Architecture 3: Hybrid (1 Worker + Celery)
*The most stable choice for a single server.*

### Overview
A single Uvicorn worker handles API requests, but hands off all "heavy lifting" to a Celery worker. Both share the same machine.

### Implementation Details
- **API Workers**: 1 Uvicorn Worker (Model loading disabled).
- **Processing Workers**: 1 Celery Worker (Loads BGE-M3).
- **Broker**: Redis.
- **Workflow**: API worker receives request -> Redis -> Celery worker processes -> Updates DB.

### Pros & Cons
| Pros | Cons |
| :--- | :--- |
| **Stability**: API and AI are in separate OS processes. API never freezes. | **Overhead**: Requires Redis and a second process to manage. |
| **Predictable RAM**: Exactly one copy of the model is loaded. | **Complexity**: Slightly harder to debug than a single-process script. |

---

## Summary Recommendation

| Metric | 1 Worker (Standard) | 4 Workers (Scalable) | Hybrid (1 Worker + Celery) |
| :--- | :--- | :--- | :--- |
| **Total RAM** | ~2.5 GB | ~3.5 GB | ~2.6 GB |
| **Concurrent Uploads** | Sequential | Parallel | Sequential base (Parallel if scaling Celery) |
| **UI Responsiveness** | Good | Excellent | Excellent |
| **Stability** | Medium | High | High |
| **Complexity** | Low | Medium | Medium |

### Transition Plan
1. **Current Status**: Architecture 1 (1 Worker + Thread Offloading) is implemented.
2. **Next Logical Step**: Architecture 3 (Hybrid) if the server becomes unresponsive during processing.
3. **Enterprise Level**: Architecture 2 (Multiple API Workers) for high request volumes.
