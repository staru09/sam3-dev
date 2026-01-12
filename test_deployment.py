#!/usr/bin/env python3
"""
Test script for deployed SAM3 Video API
Tests video segmentation with a local MP4 file
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests


def test_health(service_url: str):
    """Test the /health endpoint"""
    print("\n" + "="*60)
    print("Testing Health Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{service_url}/health", timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Status: {data['status']}")
        print(f"✓ GPU Available: {data['gpu_available']}")
        print(f"✓ Model Loaded: {data['model_loaded']}")
        print(f"✓ GPU Name: {data.get('gpu_name', 'N/A')}")
        print(f"✓ CUDA Version: {data.get('cuda_version', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_segmentation(
    service_url: str,
    video_path: str,
    prompt: str = "dog",
    background_mode: str = "black",
    output_format: str = "mp4",
    include_overlay: bool = False,
    output_dir: str = "test_outputs"
):
    """Test video segmentation"""
    print("\n" + "="*60)
    print("Testing Video Segmentation")
    print("="*60)
    
    if not os.path.exists(video_path):
        print(f"✗ Video file not found: {video_path}")
        return False
    
    # Prepare the request
    print(f"Input video: {video_path}")
    print(f"Prompt: {prompt}")
    print(f"Background mode: {background_mode}")
    print(f"Output format: {output_format}")
    print(f"Include overlay: {include_overlay}")
    print("\nUploading video and processing...")
    
    try:
        with open(video_path, 'rb') as video_file:
            files = {'video': (Path(video_path).name, video_file, 'video/mp4')}
            data = {
                'prompt': prompt,
                'background_mode': background_mode,
                'output_format': output_format,
                'include_overlay': str(include_overlay).lower()
            }
            
            # Send request
            start_time = time.time()
            response = requests.post(
                f"{service_url}/segment",
                files=files,
                data=data,
                timeout=600  # 10 minutes timeout for processing
            )
            elapsed_time = time.time() - start_time
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\n✓ Processing complete in {elapsed_time:.2f} seconds")
            print(f"✓ Success: {result['success']}")
            print(f"✓ Message: {result['message']}")
            print(f"✓ Total frames: {result['total_frames']}")
            print(f"✓ Objects detected: {result['objects_detected']}")
            print(f"✓ Processing time: {result['processing_time_seconds']:.2f}s")
            
            if not result['success']:
                print("✗ Segmentation failed")
                return False
            
            # Download results
            os.makedirs(output_dir, exist_ok=True)
            
            if result.get('output_video_path'):
                output_url = f"{service_url}{result['output_video_path']}"
                output_filename = Path(result['output_video_path']).name
                output_path = os.path.join(output_dir, output_filename)
                
                print(f"\nDownloading output video...")
                print(f"URL: {output_url}")
                
                video_response = requests.get(output_url, timeout=60)
                video_response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(video_response.content)
                
                print(f"✓ Saved to: {output_path}")
            
            if result.get('overlay_video_path'):
                overlay_url = f"{service_url}{result['overlay_video_path']}"
                overlay_filename = Path(result['overlay_video_path']).name
                overlay_path = os.path.join(output_dir, overlay_filename)
                
                print(f"\nDownloading overlay video...")
                print(f"URL: {overlay_url}")
                
                overlay_response = requests.get(overlay_url, timeout=60)
                overlay_response.raise_for_status()
                
                with open(overlay_path, 'wb') as f:
                    f.write(overlay_response.content)
                
                print(f"✓ Saved to: {overlay_path}")
            
            return True
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out. Video processing may take longer.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test deployed SAM3 Video API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default dog segmentation
  python test_deployment.py https://your-service.run.app input.mp4
  
  # Test with custom prompt
  python test_deployment.py https://your-service.run.app input.mp4 --prompt "cat"
  
  # Test with transparent background (WebM output)
  python test_deployment.py https://your-service.run.app input.mp4 --background transparent --format webm
  
  # Test with overlay visualization
  python test_deployment.py https://your-service.run.app input.mp4 --overlay
        """
    )
    
    parser.add_argument(
        'service_url',
        help='Cloud Run service URL (e.g., https://sam3-api-service-xxx.run.app)'
    )
    parser.add_argument(
        'video_path',
        nargs='?',
        help='Path to input MP4 video file'
    )
    parser.add_argument(
        '--prompt',
        default='dog',
        help='Text prompt for segmentation (default: dog)'
    )
    parser.add_argument(
        '--background',
        choices=['transparent', 'black', 'white', 'blur'],
        default='black',
        help='Background mode (default: black)'
    )
    parser.add_argument(
        '--format',
        choices=['mp4', 'webm', 'mov'],
        default='mp4',
        help='Output video format (default: mp4)'
    )
    parser.add_argument(
        '--overlay',
        action='store_true',
        help='Include overlay visualization video'
    )
    parser.add_argument(
        '--output-dir',
        default='test_outputs',
        help='Directory to save output videos (default: test_outputs)'
    )
    parser.add_argument(
        '--health-only',
        action='store_true',
        help='Only test the health endpoint'
    )
    
    args = parser.parse_args()
    
    # Clean up service URL
    service_url = args.service_url.rstrip('/')
    
    print("="*60)
    print("SAM3 Video API Deployment Test")
    print("="*60)
    print(f"Service URL: {service_url}")
    
    # Test health
    health_ok = test_health(service_url)
    if not health_ok:
        print("\n⚠ Health check failed. Service may not be ready.")
        sys.exit(1)
    
    # If health-only, exit
    if args.health_only:
        print("\n✓ Health check passed!")
        sys.exit(0)
    
    # Test segmentation
    if not args.video_path:
        print("\n⚠ No video file provided. Use --health-only to skip video test.")
        parser.print_help()
        sys.exit(1)
    
    segmentation_ok = test_segmentation(
        service_url=service_url,
        video_path=args.video_path,
        prompt=args.prompt,
        background_mode=args.background,
        output_format=args.format,
        include_overlay=args.overlay,
        output_dir=args.output_dir
    )
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Health Check: {'✓ PASSED' if health_ok else '✗ FAILED'}")
    print(f"Video Segmentation: {'✓ PASSED' if segmentation_ok else '✗ FAILED'}")
    print("="*60)
    
    if health_ok and segmentation_ok:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
