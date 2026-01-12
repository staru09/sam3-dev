#!/usr/bin/env python3
"""
Test script with GCS upload support
"""

import argparse
import requests

# Get service URL
SERVICE_URL = "https://sam3-api-service-g6gkfu4ava-ez.a.run.app"

def test_with_gcs_upload(video_path: str, prompt: str = "dog"):
    """Test video segmentation with GCS upload"""
    
    print(f"Uploading {video_path} for segmentation...")
    print(f"Prompt: {prompt}")
    print(f"Will upload results to GCS bucket: nannie_sam3")
    
    with open(video_path, 'rb') as video_file:
        files = {'video': (video_path, video_file, 'video/mp4')}
        data = {
            'prompt': prompt,
            'background_mode': 'black',
            'output_format': 'mp4',
            'upload_to_gcs': 'true',  # Enable GCS upload
            'gcs_bucket': 'nannie_sam3'
        }
        
        response = requests.post(
            f"{SERVICE_URL}/segment",
            files=files,
            data=data,
            timeout=600
        )
        
        response.raise_for_status()
        result = response.json()
        
        print("\n" + "="*60)
        print("Results:")
        print("="*60)
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        print(f"Total frames: {result['total_frames']}")
        print(f"Objects detected: {result['objects_detected']}")
        print(f"Processing time: {result['processing_time_seconds']:.2f}s")
        
        if 'GCS URLs:' in result['message']:
            print("\nFiles uploaded to GCS!")
        
        return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('video', help='Path to video file')
    parser.add_argument('--prompt', default='dog', help='Segmentation prompt')
    args = parser.parse_args()
    
    test_with_gcs_upload(args.video, args.prompt)
