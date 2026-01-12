# SAM3 Video Segmentation API

## Overview

Async video segmentation API using Meta's SAM3 model. Submit jobs and poll for status.

## Base URL

```
http://localhost:8000
```

---

## Endpoints

### 1. Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "gpu_available": true,
  "model_loaded": true,
  "cuda_version": "12.6",
  "gpu_name": "NVIDIA A100"
}
```

---

### 2. Segment Dog (Primary Endpoint)

```
POST /segment/dog
```

Segments dogs from a video stored in GCS. Returns immediately with task_id.

**Parameters (Form Data):**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_bucket` | string | ✅ | - | GCS bucket containing input video |
| `video_uuid` | string | ✅ | - | UUID of the input video |
| `video_blob_path` | string | ✅ | - | Path to video in bucket |
| `background_mode` | enum | ❌ | `transparent` | `transparent`, `black`, `white`, `blur` |
| `output_format` | enum | ❌ | `mp4` | `mp4`, `webm`, `mov` |
| `include_overlay` | bool | ❌ | `false` | Include mask overlay video |
| `gcs_bucket` | string | ❌ | `nannie_sam3` | Output bucket |

**Example Request:**
```bash
curl -X POST http://localhost:8000/segment/dog \
  -F "source_bucket=datacam_videos" \
  -F "video_uuid=005d0bf7-446c-4a06-867d-5b41e0aa468c" \
  -F "video_blob_path=raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv" \
  -F "background_mode=transparent"
```

**Response (202 Accepted):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "message": "Video segmentation job queued",
  "poll_url": "/poll/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

### 3. Segment Custom Object

```
POST /segment
```

Same as `/segment/dog` but with custom prompt.

**Additional Parameter:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ❌ | `dog` | Text describing what to segment (e.g., "cat", "person") |

---

### 4. Poll Status

```
GET /poll/{task_id}
```

Check processing status and progress.

**Example Request:**
```bash
curl http://localhost:8000/poll/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response (Running):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "progress": 45.5,
  "current_frame": 45,
  "total_frames": 100,
  "message": "Processing frame 45/100"
}
```

**Response (Completed):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "progress": 100,
  "message": "Successfully segmented 1 object(s)",
  "result": {
    "success": true,
    "objects_detected": 1,
    "total_frames": 100,
    "input_uuid": "005d0bf7-446c-4a06-867d-5b41e0aa468c",
    "output_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "gcs_urls": [
      "gs://nannie_sam3/outputs/a1b2c3d4.../segmented.webm"
    ]
  }
}
```

**Response (Failed):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "failed",
  "progress": 15.0,
  "message": "Processing failed: ...",
  "error": "Error details here"
}
```

---

## Status Values

| Status | Description |
|--------|-------------|
| `queued` | Job is waiting in queue |
| `running` | Currently processing |
| `completed` | Successfully finished, check `result` |
| `failed` | Error occurred, check `error` |

---