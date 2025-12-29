#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
SAM3 Video Segmentation API Client Example

This script demonstrates how to use the SAM3 Video Segmentation API
to extract dogs from a video and remove the background.
"""

import argparse
import os
import sys
import time

import requests


def check_api_health(base_url: str) -> bool:
    """Check if the API is healthy and model is loaded."""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"API Status: {health['status']}")
            print(f"GPU Available: {health['gpu_available']}")
            print(f"Model Loaded: {health['model_loaded']}")
            if health.get('gpu_name'):
                print(f"GPU: {health['gpu_name']}")
            return health['model_loaded']
        return False
    except requests.RequestException as e:
        print(f"Error connecting to API: {e}")
        return False


def segment_dog_video(
    base_url: str,
    video_path: str,
    output_path: str,
    background_mode: str = "black",
    output_format: str = "mp4",
    include_overlay: bool = False,
) -> bool:
    """
    Segment dogs from a video using the API.
    
    Args:
        base_url: API base URL
        video_path: Path to input video
        output_path: Path to save output video
        background_mode: Background removal mode
        output_format: Output video format
        include_overlay: Include overlay visualization
    
    Returns:
        True if successful
    """
    print(f"\nProcessing video: {video_path}")
    print(f"Background mode: {background_mode}")
    print(f"Output format: {output_format}")
    print("-" * 40)
    
    # Check if file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return False
    
    # Upload and process video
    start_time = time.time()
    
    try:
        with open(video_path, "rb") as video_file:
            files = {"video": (os.path.basename(video_path), video_file)}
            data = {
                "background_mode": background_mode,
                "output_format": output_format,
                "include_overlay": str(include_overlay).lower(),
            }
            
            print("Uploading and processing video...")
            response = requests.post(
                f"{base_url}/segment/dog",
                files=files,
                data=data,
                timeout=600,  # 10 minute timeout for long videos
            )
        
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            print(f"Details: {response.text}")
            return False
        
        result = response.json()
        
        print(f"\nResult:")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message']}")
        print(f"  Total frames: {result['total_frames']}")
        print(f"  Objects detected: {result['objects_detected']}")
        print(f"  Processing time: {result['processing_time_seconds']:.2f}s")
        print(f"  Total time (incl. upload): {elapsed:.2f}s")
        
        if not result['success']:
            print("Segmentation failed - no objects detected")
            return False
        
        # Download the output video
        if result['output_video_path']:
            print(f"\nDownloading output video...")
            download_url = f"{base_url}{result['output_video_path']}"
            video_response = requests.get(download_url, timeout=300)
            
            if video_response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(video_response.content)
                print(f"Saved to: {output_path}")
            else:
                print(f"Error downloading video: {video_response.status_code}")
                return False
        
        # Download overlay if requested
        if include_overlay and result.get('overlay_video_path'):
            overlay_path = output_path.replace(".mp4", "_overlay.mp4")
            overlay_url = f"{base_url}{result['overlay_video_path']}"
            overlay_response = requests.get(overlay_url, timeout=300)
            
            if overlay_response.status_code == 200:
                with open(overlay_path, "wb") as f:
                    f.write(overlay_response.content)
                print(f"Overlay saved to: {overlay_path}")
        
        # Cleanup server files
        task_id = result['output_video_path'].split('/')[2]
        requests.delete(f"{base_url}/cleanup/{task_id}")
        print("Server cleanup complete")
        
        return True
        
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="SAM3 Video Segmentation API Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python api_client_example.py video.mp4 output.mp4
  python api_client_example.py video.mp4 output.mp4 --background black
  python api_client_example.py video.mp4 output.webm --background transparent --format webm
  python api_client_example.py video.mp4 output.mp4 --overlay
        """
    )
    
    parser.add_argument(
        "input",
        type=str,
        help="Input video file path"
    )
    parser.add_argument(
        "output",
        type=str,
        help="Output video file path"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--background",
        type=str,
        choices=["transparent", "black", "white", "blur"],
        default="black",
        help="Background mode (default: black)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["mp4", "webm", "mov"],
        default="mp4",
        help="Output format (default: mp4)"
    )
    parser.add_argument(
        "--overlay",
        action="store_true",
        help="Include overlay visualization video"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("SAM3 Video Segmentation API Client")
    print("=" * 50)
    
    # Check API health
    print(f"\nConnecting to API at {args.url}...")
    if not check_api_health(args.url):
        print("\nWarning: API may not be ready. Proceeding anyway...")
    
    # Process video
    success = segment_dog_video(
        base_url=args.url,
        video_path=args.input,
        output_path=args.output,
        background_mode=args.background,
        output_format=args.format,
        include_overlay=args.overlay,
    )
    
    if success:
        print("\n✓ Video processing complete!")
        return 0
    else:
        print("\n✗ Video processing failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

