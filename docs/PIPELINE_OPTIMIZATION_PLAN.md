# Data Processing Pipeline Optimization Plan

This document outlines the strategy to drastically reduce processing time for large-scale document ingestion (e.g., 19,000+ chunks) by implementing parallelization, streaming, and intelligent caching. 

**Performance Target**: Process a **15MB text file (~2.5M words) in under 5 minutes**.

---

## 1. Multi-Core Parallel Processing (The "4-Core" Rule)
Current text cleaning and chunking is single-threaded, using only 1 CPU core regardless of server capacity.
- **Action**: Implement `ProcessPoolExecutor` in the cleaning and chunking services.
- **Approach**: The document will be split into segments, and 4 concurrent processes will handle the regex cleaning, language detection, and metadata enrichment.
- **Goal**: Reduce "Cleaning Stage" time by ~70%.

## 2. Advanced Caching: Vector Deduplication (Hash Check)
Embedding the same text multiple times is the biggest waste of CPU/GPU resources.
- **Action**: Create an `embedding_cache` table in PostgreSQL.
- **Workflow**: 
  1. Generate a SHA-256 hash of every text chunk.
  2. Check the DB: `SELECT vector FROM embedding_cache WHERE text_hash = :hash`.
  3. If found: Reuse the vector.
  4. If not found: Send to Embedding Server and then save to cache.
- **Goal**: Skip embedding for repetitive content (headers, footers, duplicate paragraphs).

## 3. The "Conveyor Belt" Pipeline (Streaming Uploads)
Currently, we wait for the *entire* document to be embedded before uploading anything to Qdrant.
- **Action**: Implement a batch-streamed loop.
- **Approach**: 
  - Every time 100 chunks are embedded, they are immediately pushed to Qdrant.
  - While Qdrant is indexing the first 100, the Embedding Server continues working on the next 100.
- **Goal**: Parallelize I/O and Computation to eliminate "dead time" at the end of the process.

## 4. High-Throughput Embedding (Batch Size 128)
- **Target**: Tesla P40 (Restricted to **8GB VRAM**).
- **Action**: Update `BGE_M3_BATCH_SIZE` to **128**.
- **Management**: 
  - Although the P40 has 24GB total, we will cap the AI service utilization to **8GB VRAM** to preserve system stability and leave room for other processes.
  - **Batch 128 / Context 8192** for BGE-M3 typically consumes between 6GB and 7.5GB of VRAM depending on token density. This fits safely within our 8GB limit.
  - **On CPU (Fallback)**: If forced to CPU, we will cap this at 32 to prevent system RAM exhaustion.

## 5. Chunk Efficiency: Minimal Overlap
- **Action**: Increase chunk size to **500 words** and reduce overlap to **1 sentence**.
- **Rationale**: 
    - **Chunk Size (500 words)**: Reduces the total number of embedding operations by ~70% compared to the previous 150-word setting. BGE-M3 handles up to 8k tokens, so 500 words is well within the high-accuracy range.
    - **Overlap (1 sentence)**: Minimizes redundancy to speed up calculation while maintaining the semantic connection between chunks for RAG.

## 6. Single-Worker Stability
- **Action**: Use 1 dedicated Celery worker for the processing queue.
- **Rationale**: Prevents database race conditions and ensures the Tesla P40 isn't overloaded by multiple competing giant jobs, ensuring smooth and predictable completion times.

---

## Summary of Expected Gains

| Stage | Current (150 words/CPU) | Optimized (500 words/Tesla P40) | Speedup |
| :--- | :--- | :--- | :--- |
| **Cleaning** | 10 mins | < 2 mins (4 Cores) | **5x** |
| **Embedding (15MB)** | ~4 hours (CPU) | **< 3 mins (GPU @ 128)** | **~80x** |
| **Uploading** | Sequential (at end) | Concurrent/Streamed | **Overlap** |
| **Overall** | **~4 hours+** | **< 5 Minutes** | **~50x+** |

---

## Implementation Roadmap
1. **Immediate**: Refactor Cleaning Service to use `concurrent.futures`.
2. **Short-term**: Implement the 100-chunk streaming loop in `multilingual_data_processing_service`.
3. **Mid-term**: Deploy the PostgreSQL `embedding_cache` table.
