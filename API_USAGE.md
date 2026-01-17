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

**cURL Example 1 - Basic (Segment a dog with black background):**

```bash
curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment" \
  -F "video=@input.mp4" \
  -F "prompt=dog" \
  -F "background_mode=black"
```

**cURL Example 2 - Segment a cat with white background:**

```bash
curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment" \
  -F "video=@my_cat_video.mp4" \
  -F "prompt=cat" \
  -F "background_mode=white" \
  -F "output_format=mp4"
```

**cURL Example 3 - Segment a person with blurred background:**

```bash
curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment" \
  -F "video=@person_video.mp4" \
  -F "prompt=person" \
  -F "background_mode=blur" \
  -F "include_overlay=true"
```

**cURL Example 4 - Disable GCS upload:**

```bash
curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment" \
  -F "video=@input.mp4" \
  -F "prompt=dog" \
  -F "upload_to_gcs=false"
```

**Response:**

```json
{
  "success": true,
  "message": "Successfully segmented 1 object(s) matching 'dog'. GCS URLs: gs://nannie_sam3/outputs/abc-123/segmented.mp4",
  "task_id": null,
  "output_video_path": "/outputs/abc-123/segmented.mp4",
  "overlay_video_path": null,
  "total_frames": 120,
  "objects_detected": 1,
  "processing_time_seconds": 45.3
}
```

**Note:** The `/segment` endpoint processes synchronously and returns results immediately. For async processing with GCS buckets, use `/segment/dog` instead.

---

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
- `gcs_bucket` (optional, default: "nannie_sam3"): GCS bucket name for output

**cURL Example:**

```bash
# Step 1: Submit task (returns immediately with task_id)
curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment/dog" \
  -F "source_bucket=datacam_videos" \
  -F "video_uuid=005d0bf7-446c-4a06-867d-5b41e0aa468c" \
  -F "video_blob_path=raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv" \
  -F "background_mode=black" \
  -F "gcs_bucket=nannie_sam3"
```

**Response (Immediate):**

```json
{
  "success": true,
  "message": "Task queued successfully",
  "task_id": "398e4765-ad9f-405b-9b38-92abe88d9e67",
  "output_video_path": null,
  "overlay_video_path": null,
  "total_frames": 0,
  "objects_detected": 0,
  "processing_time_seconds": 0.0
}
```

**Note:** Use the returned `task_id` to poll for progress using `/poll/{task_id}` endpoint.

---

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

---

## 🐍 Python Examples

### Example 1: File Upload (Synchronous) - `/segment`

Process a video by uploading the file directly. Returns results immediately.

```python
import requests

SERVICE_URL = "https://sam3-api-service-g6gkfu4ava-ez.a.run.app"

# Upload and process video
with open('input.mp4', 'rb') as video_file:
    files = {'video': ('input.mp4', video_file, 'video/mp4')}
    data = {
        'prompt': 'dog',
        'background_mode': 'black',
        'output_format': 'mp4'
    }
  
    response = requests.post(f"{SERVICE_URL}/segment", files=files, data=data, timeout=600)
    result = response.json()
  
    print(f"Success: {result['success']}")
    print(f"Output: {result['output_video_path']}")
    print(f"Objects detected: {result['objects_detected']}")
    print(f"Processing time: {result['processing_time_seconds']:.2f}s")

# Download the result from GCS (outputs are uploaded to GCS automatically)
# Check the message field for GCS URLs
if "GCS URLs:" in result.get('message', ''):
    print(f"GCS URL: {result['message']}")
```

### Example 2: GCS-based Async Processing with Polling - `/segment/dog`

Process a video from GCS bucket with async processing and polling.

```python
import requests
import time

SERVICE_URL = "https://sam3-api-service-g6gkfu4ava-ez.a.run.app"

# Step 1: Submit task to /segment/dog
response = requests.post(
    f"{SERVICE_URL}/segment/dog",
    data={
        "source_bucket": "datacam_videos",
        "video_uuid": "005d0bf7-446c-4a06-867d-5b41e0aa468c",
        "video_blob_path": "raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv",
        "background_mode": "black",
        "output_format": "mp4",
        "gcs_bucket": "nannie_sam3",
    },
    timeout=30
)

result = response.json()
task_id = result['task_id']
print(f"Task submitted! Task ID: {task_id}")

# Step 2: Poll for progress
max_attempts = 240  # 20 minutes max
poll_interval = 5  # seconds

for attempt in range(max_attempts):
    poll_response = requests.get(
        f"{SERVICE_URL}/poll/{task_id}",
        timeout=(5, 30)  # (connect, read) timeout
    )
  
    poll_result = poll_response.json()
    status = poll_result['status']
    progress = poll_result['progress']
  
    print(f"Status: {status} | Progress: {progress*100:.1f}% | Frame: {poll_result['current_frame']}/{poll_result['total_frames']}")
  
    if status == "completed":
        print("\n✅ Task completed!")
        result_data = poll_result.get('result', {})
        print(f"Objects detected: {result_data.get('objects_detected')}")
        print(f"Processing time: {result_data.get('processing_time_seconds'):.2f}s")
        print(f"GCS URL: {poll_result['message']}")
        break
    elif status == "failed":
        print(f"\n❌ Task failed: {poll_result['message']}")
        break
  
    time.sleep(poll_interval)
```

### Example 3: Complete Workflow with Error Handling

```python
import requests
import time
import sys

SERVICE_URL = "https://sam3-api-service-g6gkfu4ava-ez.a.run.app"

# 1. Check health
health = requests.get(f"{SERVICE_URL}/health").json()
print(f"GPU Available: {health['gpu_available']}")
print(f"Model Loaded: {health['model_loaded']}")

if not health['model_loaded']:
    print("⚠️  Model not loaded. Processing may fail.")
    sys.exit(1)

# 2. Submit async task
try:
    response = requests.post(
        f"{SERVICE_URL}/segment/dog",
        data={
            "source_bucket": "datacam_videos",
            "video_uuid": "005d0bf7-446c-4a06-867d-5b41e0aa468c",
            "video_blob_path": "raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv",
            "background_mode": "black",
            "gcs_bucket": "nannie_sam3",
        },
        timeout=30
    )
    response.raise_for_status()
    result = response.json()
    task_id = result['task_id']
    print(f"✅ Task queued: {task_id}")
except requests.RequestException as e:
    print(f"❌ Failed to submit task: {e}")
    sys.exit(1)

# 3. Poll for completion
print("\nPolling for progress...")
for attempt in range(240):  # 20 minutes max
    try:
        poll_response = requests.get(
            f"{SERVICE_URL}/poll/{task_id}",
            timeout=(5, 30)
        )
        poll_result = poll_response.json()
    
        status = poll_result['status']
        progress = poll_result['progress']
        current_frame = poll_result['current_frame']
        total_frames = poll_result['total_frames']
    
        # Display progress bar
        bar_length = 50
        filled = int(progress * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r[{bar}] {progress*100:.1f}% | {status} | {current_frame}/{total_frames}", end="", flush=True)
    
        if status == "completed":
            print("\n\n✅ Processing complete!")
            result_data = poll_result.get('result', {})
            print(f"  Objects: {result_data.get('objects_detected')}")
            print(f"  Time: {result_data.get('processing_time_seconds'):.2f}s")
            print(f"  GCS: {poll_result['message']}")
            break
        elif status == "failed":
            print(f"\n\n❌ Processing failed: {poll_result['message']}")
            sys.exit(1)
    
        time.sleep(5)
    except requests.Timeout:
        # Timeout is OK, continue polling
        time.sleep(5)
        continue
    except requests.RequestException as e:
        print(f"\n⚠️  Poll error: {e}")
        time.sleep(5)
        continue
```

---

## 🎬 Common Use Cases

### Use Case 1: Process Video from GCS with Polling

```bash
# Step 1: Submit task
TASK_RESPONSE=$(curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment/dog" \
  -F "source_bucket=datacam_videos" \
  -F "video_uuid=005d0bf7-446c-4a06-867d-5b41e0aa468c" \
  -F "video_blob_path=raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv" \
  -F "background_mode=black" \
  -F "gcs_bucket=nannie_sam3")

# Extract task_id
TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
echo "Task ID: $TASK_ID"

# Step 2: Poll for completion
while true; do
  POLL_RESPONSE=$(curl -s "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/poll/$TASK_ID")
  STATUS=$(echo $POLL_RESPONSE | jq -r '.status')
  PROGRESS=$(echo $POLL_RESPONSE | jq -r '.progress')
  
  echo "Status: $STATUS | Progress: $(echo "$PROGRESS * 100" | bc)%"
  
  if [ "$STATUS" = "completed" ]; then
    echo "✅ Task completed!"
    echo $POLL_RESPONSE | jq '.result'
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "❌ Task failed"
    echo $POLL_RESPONSE | jq -r '.message'
    exit 1
  fi
  
  sleep 5
done
```

### Use Case 2: File Upload (Synchronous Processing)

```bash
# Process video by uploading file directly
curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment" \
  -F "video=@dog_playing.mp4" \
  -F "prompt=dog" \
  -F "background_mode=black" \
  -o response.json

# Check result
cat response.json | jq '.'
```

### Use Case 3: Create Transparent Background Video

```bash
curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment" \
  -F "video=@person.mp4" \
  -F "prompt=person" \
  -F "background_mode=transparent" \
  -F "output_format=webm"
```

---

## 📦 GCS Bucket Storage

All processed videos are automatically uploaded to GCS:

**Location:** `gs://nannie_sam3/outputs/<task_id>/`

**Important Notes:**

- `/segment/dog` endpoint automatically cleans up local files after processing and GCS upload
- Only the processed output is stored in GCS (input video is not saved)
- GCS URLs are included in the poll response message when task completes

**List outputs:**

```bash
gsutil ls gs://nannie_sam3/outputs/
```

**Download from GCS:**

```bash
gsutil cp gs://nannie_sam3/outputs/68cd0253-4431-401a-85bf-65ac1bf5aacf/segmented.mp4 ./
```

**Download all outputs:**

```bash
gsutil -m cp -r gs://nannie_sam3/outputs/* ./local_outputs/
```

---

## 🔧 Testing

### Using example_runner.py

Use the provided test script for GCS-based async processing:

```bash
# Update GCS configuration in example_runner.py, then run:
python example_runner.py
```

The script will:

1. Check API health
2. Submit task to `/segment/dog`
3. Poll for progress with real-time updates
4. Display final results when complete

---

## 🎯 Interactive API Documentation

Visit the auto-generated Swagger UI documentation:

```
https://sam3-api-service-g6gkfu4ava-ez.a.run.app/docs
```

Test all endpoints directly in your browser!

---

## ⚙️ Configuration

### Background Modes

- **black**: Solid black background (fast, works with all formats)
- **white**: Solid white background (fast, works with all formats)
- **blur**: Blurred version of original background (moderate speed)
- **transparent**: Alpha channel transparency (requires WebM/MOV format)

### Supported Video Formats

**Input:** MP4, MOV, AVI, MKV, WebM, M4V
**Output:** MP4, WebM, MOV

### Segmentation Prompts

Use natural language to describe what to segment:

- "dog"
- "cat"
- "person"
- "car"
- "bird"
- "person with red shirt"
- Any object description SAM3 can understand

---

## 🚨 Troubleshooting

### 500 Internal Server Error

- Check if model is loaded: `curl <service-url>/health`
- Verify video format is supported
- Check Cloud Run logs: `gcloud run services logs read sam3-api-service --region=europe-west4`

### Timeout Errors

- Video processing can take time (30s - 2min depending on length)
- For `/segment` (file upload): Increase timeout in your client: `timeout=600` (10 minutes)
- For `/segment/dog` (async): Polling may experience timeouts if server is busy - this is normal, polling will continue automatically
- Check GPU availability in health endpoint

### No Objects Detected

- Try a clearer, more specific prompt
- Ensure the object is visible in the video
- Try with `include_overlay=true` to see what was detected

### Polling Timeout Warnings

- If you see timeout warnings during polling, this is normal when the server is busy processing
- The polling logic will automatically retry and continue
- Timeouts don't affect the actual processing - the task continues in the background
- Increase poll timeout if needed (default is 30 seconds read timeout)

---

## 📊 Performance

- **GPU**: NVIDIA L4 (24GB VRAM) or NVIDIA A100 (80GB VRAM)
- **Processing Speed**: ~2-5 FPS depending on resolution
- **Max Video Length**: ~15 minutes (adjust timeout as needed)
- **Concurrent Requests**: 1 (GPU exclusive access)
- **Async Processing**: `/segment/dog` processes in background, allowing immediate response
- **Automatic Cleanup**: Local files are automatically removed after GCS upload (no manual cleanup needed)

---

## 🔐 Security Notes

- Service is currently configured with `--allow-unauthenticated`
- To add authentication, update Cloud Run settings
- Consider adding API key authentication for production use

---

## 📝 Additional Resources

- **Cloud Run Console**: https://console.cloud.google.com/run
- **GCS Console**: https://console.cloud.google.com/storage/browser/nannie_sam3
- **Logs**: `gcloud run services logs read sam3-api-service --region=europe-west4 --limit=50`

---

## 🎉 Quick Start

### Option 1: GCS-based Async Processing (Recommended for Production)

```bash
# 1. Check service is running
curl https://sam3-api-service-405737646974.europe-west4.run.app/health

# 2. Submit task to process video from GCS
TASK_RESPONSE=$(curl -X POST "https://sam3-api-service-405737646974.europe-west4.run.app/segment/dog" \
  -F "source_bucket=datacam_videos" \
  -F "video_uuid=your-video-uuid" \
  -F "video_blob_path=videos/your-video.mp4" \
  -F "background_mode=black" \
  -F "gcs_bucket=nannie_sam3")

TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
echo "Task ID: $TASK_ID"

# 3. Poll for completion
curl "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/poll/$TASK_ID" | jq '.'

# 4. Results are automatically uploaded to GCS
# Check the message field in poll response for GCS URLs
```

### Option 2: File Upload (Synchronous)

```bash
# 1. Check service is running
curl https://sam3-api-service-g6gkfu4ava-ez.a.run.app/health

# 2. Process a video by uploading file
curl -X POST "https://sam3-api-service-g6gkfu4ava-ez.a.run.app/segment" \
  -F "video=@input.mp4" \
  -F "prompt=dog" \
  -F "background_mode=black" \
  -o response.json

# 3. Check result
cat response.json | jq '.'
# Outputs are automatically uploaded to GCS (check message field for URLs)
```
