import requests
import time
import sys
from typing import Optional

# Configuration
API_BASE_URL = "https://sam3-api-service-405737646974.europe-west4.run.app"
VIDEO_URL = "https://storage.cloud.google.com/datacam_videos/raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv"
VIDEO_ID = "005d0bf7-446c-4a06-867d-5b41e0aa468c"
POLL_INTERVAL = 1  # seconds
MAX_POLL_TIME = 30  # Maximum time to poll (1 hour)
MAX_POLL_ATTEMPTS = None  # None = unlimited, or set a number like 3600

# Extract bucket and blob path from URL
# URL format: https://storage.cloud.google.com/{bucket}/{blob_path}
source_bucket = "datacam_videos"
video_blob_path = "raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv"

print(f"Testing deployed SAM3 API at: {API_BASE_URL}")
print(f"Video URL: {VIDEO_URL}")
print(f"Video ID: {VIDEO_ID}")
print("-" * 60)

# Step 1: Submit segmentation job
print("\n[1/2] Submitting segmentation job...")
try:
    response = requests.post(
        f"{API_BASE_URL}/segment/dog",
        data={
            "source_bucket": source_bucket,
            "video_uuid": VIDEO_ID,
            "video_blob_path": video_blob_path,
            "background_mode": "black"
        },
        timeout=30  # 30 second timeout for initial request
    )
except requests.exceptions.RequestException as e:
    print(f"✗ Network error submitting job: {e}")
    sys.exit(1)

print(f"Status Code: {response.status_code}")

if response.status_code != 202:
    print(f"✗ Error: Expected 202 Accepted, got {response.status_code}")
    print(f"Response: {response.text}")
    sys.exit(1)

try:
    result = response.json()
except ValueError as e:
    print(f"✗ Error parsing JSON response: {e}")
    print(f"Response text: {response.text}")
    sys.exit(1)

task_id = result.get("task_id")
poll_url = result.get("poll_url")

if not task_id or not poll_url:
    print(f"✗ Error: Missing task_id or poll_url in response")
    print(f"Response: {result}")
    sys.exit(1)

print(f"✓ Job submitted successfully!")
print(f"  Task ID: {task_id}")
print(f"  Status: {result.get('status')}")
print(f"  Message: {result.get('message')}")

# Step 2: Poll for status
print(f"\n[2/2] Polling for progress (every {POLL_INTERVAL}s)...")
print("-" * 60)

start_time = time.time()
poll_count = 0

while True:
    # Check timeout
    elapsed_time = time.time() - start_time
    if elapsed_time > MAX_POLL_TIME:
        print(f"\n\n✗ Timeout: Polling exceeded {MAX_POLL_TIME} seconds")
        sys.exit(1)
    
    # Check max attempts
    if MAX_POLL_ATTEMPTS is not None:
        poll_count += 1
        if poll_count > MAX_POLL_ATTEMPTS:
            print(f"\n\n✗ Timeout: Exceeded {MAX_POLL_ATTEMPTS} polling attempts")
            sys.exit(1)
    
    try:
        poll_response = requests.get(
            f"{API_BASE_URL}{poll_url}",
            timeout=30  # 30 second timeout for each poll
        )
    except requests.exceptions.RequestException as e:
        print(f"\n\n✗ Network error while polling: {e}")
        print("Retrying in 5 seconds...")
        time.sleep(5)
        continue
    
    if poll_response.status_code != 200:
        print(f"\n\n✗ Error polling: HTTP {poll_response.status_code}")
        print(f"Response: {poll_response.text}")
        sys.exit(1)
    
    try:
        status_data = poll_response.json()
    except ValueError as e:
        print(f"\n\n✗ Error parsing poll response JSON: {e}")
        print(f"Response text: {poll_response.text}")
        sys.exit(1)
    
    status = status_data.get("status")
    progress = max(0, min(100, status_data.get("progress", 0)))  # Clamp between 0-100
    message = status_data.get("message", "")
    current_frame = status_data.get("current_frame", 0)
    total_frames = status_data.get("total_frames", 0)
    
    # Display progress with frame info if available
    progress_bar_length = 50
    filled_length = int(progress_bar_length * progress / 100)
    progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
    
    frame_info = ""
    if total_frames > 0:
        frame_info = f" | Frame {current_frame}/{total_frames}"
    
    print(f"\r[{progress_bar}] {progress:.1f}% | {status.upper():8s} | {message}{frame_info}", end="", flush=True)
    
    if status == "completed":
        print("\n\n✓ Processing completed successfully!")
        if "result" in status_data:
            result_data = status_data["result"]
            print(f"\nResults:")
            print(f"  Objects detected: {result_data.get('objects_detected', 'N/A')}")
            print(f"  Total frames: {result_data.get('total_frames', 'N/A')}")
            if "gcs_urls" in result_data:
                print(f"  Output URLs:")
                for url in result_data["gcs_urls"]:
                    print(f"    - {url}")
        break
    elif status == "failed":
        print(f"\n\n✗ Processing failed!")
        if "error" in status_data:
            print(f"  Error: {status_data['error']}")
        sys.exit(1)
    elif status not in ["queued", "running"]:
        # Unknown status
        print(f"\n\n✗ Unknown status: {status}")
        print(f"  Full response: {status_data}")
        sys.exit(1)
    
    time.sleep(POLL_INTERVAL)

print("\n" + "-" * 60)
print("Done!")

