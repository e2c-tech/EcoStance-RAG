# Background Processing Implementation

## Overview

The RAG system now supports background processing for file uploads, preventing API timeouts and improving user experience for large files.

## Key Features

### 1. Asynchronous Processing
- File processing runs in background tasks
- API returns immediately with job ID
- No more blocking on large file uploads

### 2. Job Tracking
- Unique job IDs for each processing task
- Real-time status updates (pending, processing, completed, failed)
- Progress messages throughout the pipeline

### 3. Status Monitoring
- REST API endpoints for job status checking
- Automatic cleanup of old jobs
- Job listing for debugging/monitoring

## API Endpoints

### Start Processing
```
POST /api/v1/upload-to-qdrant/
```

**Request:**
```json
{
  "file_path": "/path/to/uploaded/file.pdf",
  "collection_name": "my_knowledge_base"
}
```

**Response:**
```json
{
  "message": "Processing started for 'file.pdf' in collection 'my_knowledge_base'.",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status_url": "/api/v1/processing-status/550e8400-e29b-41d4-a716-446655440000"
}
```

### Check Job Status
```
GET /api/v1/processing-status/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "file_path": "/path/to/file.pdf",
  "collection_name": "my_knowledge_base",
  "created_at": "2025-11-11T10:30:00",
  "started_at": "2025-11-11T10:30:05",
  "completed_at": null,
  "error_message": null,
  "progress_message": "Step 3/5: Chunking complete. Generated 45 chunks."
}
```

### List All Jobs
```
GET /api/v1/jobs/
```

**Response:**
```json
{
  "total_jobs": 3,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "file_path": "/path/to/file.pdf",
      "collection_name": "my_knowledge_base",
      "created_at": "2025-11-11T10:30:00",
      "started_at": "2025-11-11T10:30:05",
      "completed_at": "2025-11-11T10:32:15",
      "error_message": null,
      "progress_message": "Pipeline finished successfully for file: file.pdf"
    }
  ]
}
```

## Job Status Values

- **pending**: Job created but not yet started
- **processing**: Job is currently running
- **completed**: Job finished successfully
- **failed**: Job encountered an error

## Progress Messages

The system provides detailed progress messages during processing:

1. "Starting full processing pipeline for file: filename.pdf"
2. "Step 1/5: Starting document extraction..."
3. "Step 1/5: Extraction complete. Found 25 blocks."
4. "Step 2/5: Starting data cleaning and enrichment..."
5. "Step 2/5: Cleaning complete. 23 blocks remain after cleaning."
6. "Step 3/5: Starting text chunking..."
7. "Step 3/5: Chunking complete. Generated 45 chunks."
8. "Step 4/5: Starting embedding generation..."
9. "Step 4/5: Embedding complete. All 45 chunks have been embedded."
10. "Step 5/5: Starting upload to vector database..."
11. "Step 5/5: Upload to Qdrant complete."
12. "Pipeline finished successfully for file: filename.pdf"

## Streamlit UI Integration

The Streamlit UI has been updated to support background processing:

### Features:
- **Immediate Feedback**: Shows job ID when processing starts
- **Real-time Monitoring**: Displays current status and progress
- **Auto-refresh**: Updates status automatically for active jobs
- **Job Management**: Remove completed/failed jobs from the list
- **Auto-cleanup**: Removes old jobs after 5 minutes

### Usage:
1. Upload a file and click "Upload and Process"
2. System returns immediately with job ID
3. Monitor progress in the "Processing Jobs" section
4. Jobs auto-refresh until completion
5. Completed jobs can be manually removed

## Automatic Cleanup

The system includes automatic cleanup of old jobs:

- **Cleanup Service**: Runs every hour by default
- **Job Retention**: Jobs older than 24 hours are automatically removed
- **Configurable**: Cleanup intervals and retention periods can be adjusted
- **Health Monitoring**: Cleanup service status available via `/health` endpoint

## Error Handling

### Common Error Scenarios:
1. **File Not Found**: Returns 404 if uploaded file doesn't exist
2. **Processing Failures**: Job status shows "failed" with error message
3. **Invalid Job ID**: Returns 404 for non-existent job IDs

### Error Recovery:
- Failed jobs retain error messages for debugging
- Users can retry processing by uploading the file again
- System continues processing other jobs even if one fails

## Performance Benefits

### Before (Synchronous):
- API blocked until processing complete
- Timeouts on large files (>50MB)
- Poor user experience for slow operations
- No progress visibility

### After (Asynchronous):
- Immediate API response (<100ms)
- No timeouts regardless of file size
- Real-time progress updates
- Better resource utilization

## Testing

Run the background processing test:

```bash
python tests/test_background_processing.py
```

This test verifies:
- Job creation and immediate response
- Status tracking throughout processing
- Progress message updates
- Successful completion and data availability
- Job listing functionality

## Configuration

### Job Tracker Settings:
- Thread-safe job storage
- UUID-based job IDs
- Automatic cleanup of old jobs

### Cleanup Service Settings:
```python
# In app/services/cleanup_service.py
cleanup_service = CleanupService(
    cleanup_interval_hours=1,    # Run cleanup every hour
    max_job_age_hours=24        # Remove jobs older than 24 hours
)
```

## Migration Notes

### Breaking Changes:
- `/upload-to-qdrant/` endpoint now returns job ID instead of completion message
- Clients must poll `/processing-status/{job_id}` for completion

### Backward Compatibility:
- All other endpoints remain unchanged
- Existing knowledge bases and data are unaffected
- Query functionality works identically

## Monitoring and Debugging

### Health Check:
```
GET /health
```

Returns system health including cleanup service status.

### Job Monitoring:
- Use `/jobs/` endpoint to see all current jobs
- Monitor job completion rates and error patterns
- Track processing times for performance optimization

### Logging:
- All job state changes are logged
- Progress messages appear in application logs
- Error details captured for failed jobs