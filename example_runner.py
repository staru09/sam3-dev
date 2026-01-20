import requests
import time
import sys
import os
import shutil


SERVICE_URL = "https://sam3-api-service-405737646974.europe-west4.run.app"

video_url = "https://storage.cloud.google.com/datacam_videos/raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv"
video_id = "005d0bf7-446c-4a06-867d-5b41e0aa468c"


SOURCE_BUCKET = "datacam_videos"  # GCS bucket containing the input video
VIDEO_UUID = video_id  # UUID of the input video
VIDEO_BLOB_PATH = "raw_videos/005d0bf7-446c-4a06-867d-5b41e0aa468c.mkv"  # Path to video blob in source bucket

# Local output folder for saving downloaded videos
OUTPUT_FOLDER = "datacam_videos/processed_videos"

# GCS output path for processed videos (format: bucket/folder)
GCS_OUTPUT_PATH = "datacam_videos/processed_videos"


def check_api_health(base_url: str, max_retries: int = 5, retry_delay: int = 5) -> bool:
    """
    Check if the API is healthy and model is loaded.
    Retries if model is not loaded yet.
    """
    print(f"Checking API health at {base_url}...")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=10)
            if response.status_code == 200:
                health = response.json()
                print(f"API Status: {health['status']}")
                print(f"GPU Available: {health['gpu_available']}")
                print(f"Model Loaded: {health['model_loaded']}")
                if health.get('gpu_name'):
                    print(f"GPU: {health['gpu_name']}")
                
                if health['model_loaded']:
                    print("✅ Model is ready!")
                    return True
                else:
                    if attempt < max_retries - 1:
                        print(f"⚠️  Model not loaded yet. Waiting {retry_delay}s before retry ({attempt + 1}/{max_retries})...")
                        print("   Note: If this persists, ensure the server is configured to download weights from HuggingFace.")
                        print("   The server should use 'load_from_HF=True' in build_sam3_video_predictor()")
                        time.sleep(retry_delay)
                    else:
                        print("\n❌ Model failed to load after multiple attempts.")
                        print("\nServer Configuration Issue:")
                        print("The API server needs to be configured to download weights from HuggingFace.")
                        print("Update api/services/sam3_service.py to use:")
                        print("  - build_sam3_video_predictor(load_from_HF=True, checkpoint_path=None)")
                        print("  - This will automatically download weights from 'facebook/sam3' on HuggingFace")
                        return False
            else:
                print(f"⚠️  Health check returned status {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        except requests.RequestException as e:
            print(f"⚠️  Error connecting to API: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print("\n❌ Failed to connect to API after multiple attempts.")
                return False
    
    return False


def check_polling_endpoint(base_url: str) -> bool:
    """
    Check if the polling endpoint is accessible.
    Tests with a dummy task_id to verify the endpoint responds correctly.
    """
    print(f"\nChecking polling endpoint at {base_url}/poll/...") 
    
    try:
        # Test with a dummy task_id - should return 404 (task not found)
        response = requests.get(f"{base_url}/poll/test-dummy-task-id", timeout=10)
        
        if response.status_code == 404:
            print("✅ Polling endpoint is accessible (returned 404 for non-existent task as expected)")
            return True
        elif response.status_code == 200:
            print("✅ Polling endpoint is accessible")
            return True
        else:
            print(f"⚠️  Polling endpoint returned unexpected status: {response.status_code}")
            return True  # Still accessible, just unexpected response
            
    except requests.RequestException as e:
        print(f"❌ Error connecting to polling endpoint: {e}")
        return False


# Check API health first
print("=" * 60)
print("SAM3 Video Segmentation API - Test Runner")
print("=" * 60)

if not check_api_health(SERVICE_URL):
    print("\n⚠️  Model not loaded. The request may fail.")
    print("Continuing anyway...")

# Check polling endpoint
if not check_polling_endpoint(SERVICE_URL):
    print("\n⚠️  Polling endpoint not accessible. Progress tracking may fail.")
    print("Continuing anyway...")

print(f"\nTesting /segment/dog endpoint with polling")
print("-" * 60)

print(f"Configuration:")
print(f"  Source Bucket: {SOURCE_BUCKET}")
print(f"  Video UUID: {VIDEO_UUID}")
print(f"  Video Blob Path: {VIDEO_BLOB_PATH}")
print(f"  Output Path: gs://{GCS_OUTPUT_PATH}/")
print()

# Step 1: Submit task to /segment/dog
try:
    print("Step 1: Submitting task to /segment/dog...")
    response = requests.post(
        f"{SERVICE_URL}/segment/dog",
        data={
            "source_bucket": SOURCE_BUCKET,
            "video_uuid": VIDEO_UUID,
            "video_blob_path": VIDEO_BLOB_PATH,
            "background_mode": "black",
            "output_format": "mp4",
            "gcs_output_path": GCS_OUTPUT_PATH,
        },
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Error: API returned status {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
    
    result = response.json()
    print(f"✅ Task submitted successfully!")
    print(f"Task ID: {result.get('task_id')}")
    print(f"Message: {result.get('message')}")
    
    task_id = result.get('task_id')
    if not task_id:
        print("❌ Error: No task_id returned from endpoint")
        sys.exit(1)
    
except requests.RequestException as e:
    print(f"❌ Request error: {e}")
    sys.exit(1)

# Step 2: Poll for progress
print(f"\nStep 2: Polling task progress...")
print("-" * 60)

max_poll_attempts = 240  # 20 minutes max (5 second intervals)
poll_interval = 5  # seconds
poll_timeout = 30  # Increased timeout for poll requests (server might be busy)
consecutive_timeouts = 0
max_consecutive_timeouts = 3  # Only show timeout warning after 3 consecutive failures

for attempt in range(max_poll_attempts):
    try:
        poll_response = requests.get(
            f"{SERVICE_URL}/poll/{task_id}",
            timeout=(5, poll_timeout)  # (connect timeout, read timeout)
        )
        
        # Reset consecutive timeout counter on successful request
        consecutive_timeouts = 0
        
        if poll_response.status_code == 404:
            print(f"\n❌ Error: Task {task_id} not found")
            sys.exit(1)
        
        if poll_response.status_code != 200:
            print(f"\n⚠️  Poll returned status {poll_response.status_code}")
            time.sleep(poll_interval)
            continue
        
        poll_result = poll_response.json()
        status = poll_result.get('status', 'unknown')
        progress = poll_result.get('progress', 0.0)
        current_frame = poll_result.get('current_frame', 0)
        total_frames = poll_result.get('total_frames', 0)
        message = poll_result.get('message', '')
        
        # Display progress (truncate long messages for display)
        display_message = message[:50] + "..." if len(message) > 50 else message
        progress_bar = "█" * int(progress * 50) + "░" * (50 - int(progress * 50))
        print(f"\r[{progress_bar}] {progress*100:.1f}% | Status: {status} | Frame: {current_frame}/{total_frames} | {display_message}", end="", flush=True)
        
        if status == "completed":
            print("\n\n✅ Task completed successfully!")
            print("-" * 60)
            
            # Get final results from poll response
            result_data = poll_result.get('result', {})
            
            print(f"\n📊 Final Results:")
            print(f"  Status: {status}")
            print(f"  Progress: {progress*100:.1f}%")
            print(f"  Total Frames: {total_frames}")
            if message:
                print(f"  Message: {message}")
            
            if result_data:
                print(f"\n📹 Output Details:")
                if result_data.get('success'):
                    print(f"  ✅ Processing successful")
                if result_data.get('objects_detected'):
                    print(f"  Objects Detected: {result_data.get('objects_detected')}")
                if result_data.get('processing_time_seconds'):
                    print(f"  Processing Time: {result_data.get('processing_time_seconds'):.2f}s")
                if result_data.get('output_video_path'):
                    print(f"  Output Video Path: {result_data.get('output_video_path')}")
                    print(f"  GCS URL: Check message above for GCS URLs")
                if result_data.get('overlay_video_path'):
                    print(f"  Overlay Video Path: {result_data.get('overlay_video_path')}")
            else:
                # Fallback: parse message for GCS URLs
                if message and "GCS URLs:" in message:
                    print(f"\n📹 Output Details:")
                    print(f"  {message}")
            
            break
        elif status == "failed":
            print(f"\n\n❌ Task failed!")
            print(f"Error: {message}")
            sys.exit(1)
        elif status in ["queued", "processing"]:
            # Continue polling
            time.sleep(poll_interval)
        else:
            print(f"\n⚠️  Unknown status: {status}")
            time.sleep(poll_interval)
    
    except requests.Timeout as e:
        consecutive_timeouts += 1
        # Only show warning after multiple consecutive timeouts
        if consecutive_timeouts >= max_consecutive_timeouts:
            print(f"\n⚠️  Poll timeout (attempt {attempt + 1}/{max_poll_attempts}) - server may be busy processing. Retrying...")
            consecutive_timeouts = 0  # Reset after warning
        # Continue polling - timeouts are not fatal
        time.sleep(poll_interval)
        continue
    except requests.RequestException as e:
        # For other request errors, show warning but continue
        if "Read timed out" not in str(e):  # Suppress read timeout messages (handled above)
            print(f"\n Poll error: {e}")
        time.sleep(poll_interval)
        continue

if attempt >= max_poll_attempts - 1:
    print(f"\n\n  Timeout: Task did not complete within {max_poll_attempts * poll_interval} seconds")
    print(f"Task ID: {task_id}")
    print("You can continue polling manually using:")
    print(f"  curl {SERVICE_URL}/poll/{task_id}")
    sys.exit(1)

# API saves directly to gs://datacam_videos/processed_videos/{task_id}.mp4
# No copy step needed - output is already in the correct location
gcs_output_path = f"gs://datacam_videos/processed_videos/{task_id}.mp4"
print(f"\n📹 Output video saved to: {gcs_output_path}")

print("\n" + "=" * 60)
print("Test completed successfully!")
print("=" * 60)

