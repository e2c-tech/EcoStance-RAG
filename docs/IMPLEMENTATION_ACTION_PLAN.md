# Tactical Implementation Plan: 5-Minute Processing Goal

This document defines the step-by-step technical execution plan to achieve the target of processing a **15MB text file in under 5 minutes**.

---

## Phase 1: Efficiency Tuning (The "Quick Wins")
*Goal: Reduce the total number of operations.*

*   **Step 1.1: Re-configure Chunking Defaults**
    *   Update `chunking_service.py` to use `target_chunk_words = 500` and `overlap_sentences = 1`.
    *   *Impact*: Reduces total chunks by ~70%, dramatically lowering embedding and upload count.
*   **Step 1.2: Global Batch Update**
    *   Update `app/config` and `embedding_server.py` to support `BGE_M3_BATCH_SIZE = 128`.
    *   *Impact*: Maximizes Tesla P40 GPU throughput.

---

## Phase 2: Parallelizing CPU-Bound Work
*Goal: Use all 4 CPU cores for the non-AI stages.*

*   **Step 2.1: Multi-Core Cleaning**
    *   Refactor `multilingual_cleaning_service.py` using `ProcessPoolExecutor`.
    *   Distribute document blocks across 4 CPU processes for regex cleaning and language detection.
*   **Step 2.2: Parallel Chunking**
    *   Apply the same `ProcessPoolExecutor` strategy to `chunking_service.py` if the block count is high.

---

## Phase 3: The "Conveyor Belt" (Streaming I/O)
*Goal: Eliminate idle time between stages.*

*   **Step 3.1: Batching the Main Pipeline**
    *   Modify `multilingual_data_processing_service.py` to use a generator/loop for batches of 100 chunks.
    *   Pipeline sequence: `Extract -> Clean -> Chunk -> [Embed Batch -> Upload Batch]`.
*   **Step 3.2: Async Overlap**
    *   Ensure the Celery worker performs the next `Embed` request while the current `Upload` is still in flight to Qdrant.

---

## Phase 4: Caching & Deduplication
*Goal: Stop embedding text we have seen before.*

*   **Step 4.1: Hash Table Integration**
    *   Implement a SHA-256 hashing check at the start of the `Embed` stage.
*   **Step 4.2: Vector Reuse**
    *   Query the existing vector store for the hash. If the vector exists, skip the Embedding Server call entirely.

---

## Phase 5: Monitoring & Verification
*Goal: Data-driven proof of performance.*

*   **Step 5.1: Performance Logging**
    *   Add micro-timers to every stage (Extraction Time, Cleaning Time, Embedding Time).
*   **Step 5.2: 15MB Stress Test**
    *   Run a benchmarking job with a 15MB file and verify the < 5-minute completion time via Celery logs.
