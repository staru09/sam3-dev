# SAM3 Video API - Deployment Guide

A GPU-accelerated video segmentation API powered by Meta's SAM3 (Segment Anything Model 3), deployed on Google Cloud Run.

## 🌐 Service URL

```
https://sam3-api-service-405737646974.europe-west4.run.app
```

Replace with your actual deployed service URL.

---

## 📋 Available Endpoints

### 1. Health Check

### 2. Root Information (Optional)

### 3. Video Segmentation (General) - File Upload

### 4. Video Segmentation (Dog-specific) - GCS-based with Async Processing

### 5. Poll Task Progress

---

## 🔍 Endpoint Details & Examples

### 1. **GET /health** - Health Check

Check API status, GPU availability, and model loading status.

**cURL Example:**

```bash
curl -X GET "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/health"
```

**Response:**

```json
{
  "status": "healthy",
  "gpu_available": true,
  "model_loaded": true,
  "cuda_version": "12.1",
  "gpu_name": "NVIDIA L4"
}
```

---

### 2. **GET /** - Root Information

Get basic API information and available endpoints.

**cURL Example:**

```bash
curl -X GET "https://sam3-api-service-405737646974.europe-west4.run.app"
```

**Response:**

```json
{
  "name": "SAM3 Video Segmentation API",
  "version": "1.0.0",
  "description": "Remove backgrounds from videos using SAM3",
  "docs": "/docs",
  "health": "/health"
}
```

---

### 3. **POST /segment** - Video Segmentation (General)

Segment any object from a video using a text prompt.

**Parameters:**

- `video` (required): Video file (MP4, MOV, AVI, MKV, WebM, M4V)
- `prompt` (optional, default: "dog"): Text description of object to segment
- `background_mode` (optional, default: "black"): Background style
  - `black` - Solid black background
  - `white` - Solid white background
  - `blur` - Blurred background
  - `transparent` - Alpha channel (requires WebM format)
- `output_format` (optional, default: "mp4"): Output video format (mp4, webm, mov)
- `include_overlay` (optional, default: false): Include visualization video
- `upload_to_gcs` (optional, default: true): Upload to GCS bucket
- `gcs_bucket` (optional, default: "nannie_sam3"): GCS bucket name

### 4. **POST /segment/dog** - Dog Segmentation from GCS (Async)

Segment dogs from a video stored in Google Cloud Storage. This endpoint queues the task and returns immediately with a `task_id`. Use the `/poll/{task_id}` endpoint to check progress. Local files are automatically cleaned up after processing and GCS upload.

**Parameters:**

- `source_bucket` (required): GCS bucket name containing the input video
- `video_uuid` (required): UUID of the input video in the source bucket
- `video_blob_path` (required): Path to video blob in bucket (e.g., `videos/input.mp4`)
- `background_mode` (optional, default: "transparent"): Background style
  - `transparent` - RGBA with transparent background (requires WebM format)
  - `black` - Solid black background
  - `white` - Solid white background
  - `blur` - Blurred version of original background
- `output_format` (optional, default: "mp4"): Output video format (mp4, webm, mov)
- `include_overlay` (optional, default: false): Include visualization video
- `upload_to_gcs` (optional, default: true): Upload results to GCS bucket
- `gcs_bucket` (optional, default: "nannie_sam3"): GCS bucket name for output.

### 5. **GET /poll/** - Poll Task Progress

Check the progress of a segmentation task submitted via `/segment/dog`.

**Parameters:**

- `task_id` (required): The task ID returned from `/segment/dog` endpoint

**cURL Example:**

```bash
curl -X GET "https://sam3-api-service-405737646974.europe-west4.run.app/poll/task_id"
```

**Response (While Processing):**

```json
{
  "task_id": "398e4765-ad9f-405b-9b38-92abe88d9e67",
  "status": "processing",
  "progress": 0.65,
  "current_frame": 213,
  "total_frames": 328,
  "message": "Processing frame 213/328",
  "result": null
}
```

**Response (When Completed):**

```json
{
  "task_id": "398e4765-ad9f-405b-9b38-92abe88d9e67",
  "status": "completed",
  "progress": 1.0,
  "current_frame": 328,
  "total_frames": 328,
  "message": "Successfully segmented 1 object(s) matching 'dog' Input UUID: 005d0bf7-446c-4a06-867d-5b41e0aa468c, Output UUID: 68cd0253-4431-401a-85bf-65ac1bf5aacf GCS URLs: gs://nannie_sam3/outputs/68cd0253-4431-401a-85bf-65ac1bf5aacf/segmented.mp4",
  "result": {
    "success": true,
    "output_video_path": "/outputs/68cd0253-4431-401a-85bf-65ac1bf5aacf/segmented.mp4",
    "overlay_video_path": null,
    "objects_detected": 1,
    "processing_time_seconds": 49.5
  }
}
```

**Status Values:**

- `queued` - Task is queued and waiting to start
- `processing` - Task is currently being processed
- `completed` - Task completed successfully (check `result` field for details)
- `failed` - Task failed (check `message` field for error details)
