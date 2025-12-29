# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Video processing utilities for SAM3 API
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np


def _convert_video_to_h264(input_path: str, output_path: str) -> bool:
    """
    Convert video to H.264 codec using FFmpeg for better compatibility.
    
    Args:
        input_path: Path to input video
        output_path: Path to output video
    
    Returns:
        True if conversion successful
    """
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-strict', 'experimental',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        print(f"FFmpeg conversion failed: {e}")
        return False


def _extract_frames_with_ffmpeg(
    video_path: str,
    output_dir: str,
    max_frames: Optional[int] = None
) -> Tuple[List[str], int, Tuple[int, int]]:
    """
    Extract frames using FFmpeg (more codec support than OpenCV).
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Get video info using ffprobe
    probe_cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,r_frame_rate,nb_frames',
        '-of', 'csv=p=0',
        video_path
    ]
    
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        parts = result.stdout.strip().split(',')
        width = int(parts[0])
        height = int(parts[1])
        # Parse frame rate (e.g., "30/1" or "30000/1001")
        fps_parts = parts[2].split('/')
        fps = int(float(fps_parts[0]) / float(fps_parts[1])) if len(fps_parts) == 2 else int(float(fps_parts[0]))
        fps = max(1, fps)  # Ensure at least 1 fps
    except Exception as e:
        print(f"FFprobe failed, using defaults: {e}")
        fps = 30
        width, height = 1920, 1080
    
    # Extract frames with ffmpeg
    output_pattern = os.path.join(output_dir, '%05d.jpg')
    
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-q:v', '2',  # High quality JPEG
    ]
    
    if max_frames:
        ffmpeg_cmd.extend(['-frames:v', str(max_frames)])
    
    ffmpeg_cmd.append(output_pattern)
    
    try:
        subprocess.run(ffmpeg_cmd, capture_output=True, timeout=600)
    except Exception as e:
        raise RuntimeError(f"FFmpeg frame extraction failed: {e}")
    
    # Get list of extracted frames
    frame_paths = sorted([
        os.path.join(output_dir, f) for f in os.listdir(output_dir)
        if f.endswith('.jpg')
    ])
    
    if not frame_paths:
        raise RuntimeError("No frames extracted from video")
    
    # Get actual dimensions from first frame
    first_frame = cv2.imread(frame_paths[0])
    if first_frame is not None:
        height, width = first_frame.shape[:2]
    
    return frame_paths, fps, (width, height)


def extract_frames_from_video(
    video_path: str,
    output_dir: str,
    max_frames: Optional[int] = None
) -> Tuple[List[str], int, Tuple[int, int]]:
    """
    Extract frames from a video file to JPEG images.
    Uses FFmpeg as fallback for problematic codecs (AV1, VP9, etc.)
    
    Args:
        video_path: Path to input video file
        output_dir: Directory to save extracted frames
        max_frames: Maximum number of frames to extract (None for all)
    
    Returns:
        Tuple of (list of frame paths, fps, (width, height))
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # First try with OpenCV
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("OpenCV failed to open video, trying FFmpeg...")
        cap.release()
        return _extract_frames_with_ffmpeg(video_path, output_dir, max_frames)
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Check if video metadata is valid
    if fps <= 0 or width <= 0 or height <= 0:
        print("Invalid video metadata, trying FFmpeg...")
        cap.release()
        return _extract_frames_with_ffmpeg(video_path, output_dir, max_frames)
    
    if max_frames:
        total_frames = min(total_frames, max_frames)
    
    frame_paths = []
    frame_idx = 0
    consecutive_failures = 0
    
    while frame_idx < total_frames:
        ret, frame = cap.read()
        
        if not ret:
            consecutive_failures += 1
            # If too many consecutive failures, switch to FFmpeg
            if consecutive_failures > 10:
                print(f"Too many read failures at frame {frame_idx}, switching to FFmpeg...")
                cap.release()
                # Clean up partial extraction
                for p in frame_paths:
                    try:
                        os.remove(p)
                    except:
                        pass
                return _extract_frames_with_ffmpeg(video_path, output_dir, max_frames)
            continue
        
        consecutive_failures = 0
        
        # Check if frame is valid (not empty/corrupt)
        if frame is None or frame.size == 0:
            continue
        
        frame_path = os.path.join(output_dir, f"{frame_idx:05d}.jpg")
        cv2.imwrite(frame_path, frame)
        frame_paths.append(frame_path)
        frame_idx += 1
    
    cap.release()
    
    # If we got no frames, try FFmpeg
    if not frame_paths:
        print("No frames extracted with OpenCV, trying FFmpeg...")
        return _extract_frames_with_ffmpeg(video_path, output_dir, max_frames)
    
    return frame_paths, fps, (width, height)


def create_video_from_frames(
    frames: List[np.ndarray],
    output_path: str,
    fps: int = 30,
    codec: str = "mp4v",
    has_alpha: bool = False
) -> str:
    """
    Create a video from a list of frames.
    
    Args:
        frames: List of numpy arrays (H, W, C)
        output_path: Path to save the output video
        fps: Frames per second
        codec: Video codec
        has_alpha: If True, save with alpha channel (requires WebM)
    
    Returns:
        Path to the created video
    """
    if not frames:
        raise ValueError("No frames provided")
    
    height, width = frames[0].shape[:2]
    
    if has_alpha and output_path.endswith('.webm'):
        # For WebM with alpha, use VP9 codec
        fourcc = cv2.VideoWriter_fourcc(*'VP90')
    else:
        fourcc = cv2.VideoWriter_fourcc(*codec)
    
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in frames:
        if frame.shape[2] == 4:  # RGBA
            # Convert RGBA to BGR for standard video
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            writer.write(frame_bgr)
        elif frame.shape[2] == 3:
            # Assume RGB, convert to BGR
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
        else:
            writer.write(frame)
    
    writer.release()
    return output_path


def create_video_with_alpha(
    frames: List[np.ndarray],
    output_path: str,
    fps: int = 30
) -> str:
    """
    Create a video with alpha channel (transparency).
    Uses PNG sequence and ffmpeg for alpha support.
    
    Args:
        frames: List of RGBA numpy arrays (H, W, 4)
        output_path: Path to save the output video
        fps: Frames per second
    
    Returns:
        Path to the created video
    """
    if not frames:
        raise ValueError("No frames provided")
    
    # Create temporary directory for PNG frames
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save frames as PNG (supports alpha)
        for idx, frame in enumerate(frames):
            if frame.shape[2] == 4:
                frame_bgra = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGRA)
            else:
                # Add alpha channel if not present
                alpha = np.ones((*frame.shape[:2], 1), dtype=np.uint8) * 255
                frame_bgra = np.concatenate([
                    cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                    alpha
                ], axis=-1)
            
            png_path = os.path.join(temp_dir, f"{idx:05d}.png")
            cv2.imwrite(png_path, frame_bgra)
        
        # Use ffmpeg to create video with alpha
        if output_path.endswith('.webm'):
            # WebM with VP9 supports alpha
            cmd = [
                'ffmpeg', '-y',
                '-framerate', str(fps),
                '-i', os.path.join(temp_dir, '%05d.png'),
                '-c:v', 'libvpx-vp9',
                '-pix_fmt', 'yuva420p',
                '-auto-alt-ref', '0',
                output_path
            ]
        elif output_path.endswith('.mov'):
            # MOV with ProRes 4444 supports alpha
            cmd = [
                'ffmpeg', '-y',
                '-framerate', str(fps),
                '-i', os.path.join(temp_dir, '%05d.png'),
                '-c:v', 'prores_ks',
                '-profile:v', '4444',
                '-pix_fmt', 'yuva444p10le',
                output_path
            ]
        else:
            # Fallback to MP4 without alpha (blend with black)
            cmd = [
                'ffmpeg', '-y',
                '-framerate', str(fps),
                '-i', os.path.join(temp_dir, '%05d.png'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                output_path
            ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
        
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def apply_mask_to_frame(
    frame: np.ndarray,
    mask: np.ndarray,
    background_mode: str = "transparent"
) -> np.ndarray:
    """
    Apply a binary mask to a frame, removing or replacing the background.
    
    Args:
        frame: Input frame (H, W, 3) in RGB format
        mask: Binary mask (H, W) where 1 is foreground
        background_mode: How to handle background
            - "transparent": RGBA with transparent background
            - "black": Black background
            - "white": White background
            - "blur": Blurred background
    
    Returns:
        Processed frame (H, W, 3 or 4)
    """
    # Ensure mask is binary and same size as frame
    if mask.shape[:2] != frame.shape[:2]:
        mask = cv2.resize(mask.astype(np.float32), (frame.shape[1], frame.shape[0]))
    
    mask = (mask > 0.5).astype(np.uint8)
    
    if background_mode == "transparent":
        # Create RGBA image with transparent background
        alpha = mask * 255
        rgba = np.dstack([frame, alpha])
        return rgba
    
    elif background_mode == "black":
        # Black background
        result = frame.copy()
        result[mask == 0] = [0, 0, 0]
        return result
    
    elif background_mode == "white":
        # White background
        result = frame.copy()
        result[mask == 0] = [255, 255, 255]
        return result
    
    elif background_mode == "blur":
        # Blurred background
        blurred = cv2.GaussianBlur(frame, (51, 51), 0)
        result = np.where(mask[..., None], frame, blurred)
        return result
    
    else:
        raise ValueError(f"Unknown background mode: {background_mode}")


def combine_masks(masks: List[np.ndarray]) -> np.ndarray:
    """
    Combine multiple masks into a single mask using logical OR.
    
    Args:
        masks: List of binary masks
    
    Returns:
        Combined mask
    """
    if not masks:
        raise ValueError("No masks provided")
    
    combined = masks[0].astype(bool)
    for mask in masks[1:]:
        combined = combined | mask.astype(bool)
    
    return combined.astype(np.uint8)


def get_video_info(video_path: str) -> dict:
    """
    Get information about a video file.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Dictionary with video information
    """
    # Try FFprobe first (more reliable for various codecs)
    try:
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,nb_frames,codec_name',
            '-show_entries', 'format=duration',
            '-of', 'json',
            video_path
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            stream = data.get('streams', [{}])[0]
            fmt = data.get('format', {})
            
            fps_parts = stream.get('r_frame_rate', '30/1').split('/')
            fps = int(float(fps_parts[0]) / float(fps_parts[1])) if len(fps_parts) == 2 else 30
            
            return {
                "width": int(stream.get('width', 0)),
                "height": int(stream.get('height', 0)),
                "fps": fps,
                "total_frames": int(stream.get('nb_frames', 0)) or int(float(fmt.get('duration', 0)) * fps),
                "duration_seconds": float(fmt.get('duration', 0)),
                "codec": stream.get('codec_name', 'unknown'),
            }
    except Exception as e:
        print(f"FFprobe failed: {e}, falling back to OpenCV")
    
    # Fallback to OpenCV
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": fps,
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration_seconds": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps if fps > 0 else 0,
        "codec": "unknown",
    }
    
    cap.release()
    return info


def load_video_frames(video_path: str) -> Tuple[List[np.ndarray], int]:
    """
    Load all frames from a video file.
    Uses FFmpeg as fallback for problematic codecs.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Tuple of (list of frames in RGB, fps)
    """
    # First try OpenCV
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        # Fallback: use FFmpeg to extract to temp dir, then load
        print("OpenCV failed to open video for frame loading, using FFmpeg...")
        return _load_frames_via_ffmpeg(video_path)
    
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    frames = []
    consecutive_failures = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            consecutive_failures += 1
            if consecutive_failures > 10:
                break
            continue
        
        consecutive_failures = 0
        
        if frame is None or frame.size == 0:
            continue
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame_rgb)
    
    cap.release()
    
    # If we got very few or no frames, try FFmpeg
    if len(frames) < 5:
        print(f"Only got {len(frames)} frames with OpenCV, trying FFmpeg...")
        return _load_frames_via_ffmpeg(video_path)
    
    return frames, fps


def _load_frames_via_ffmpeg(video_path: str) -> Tuple[List[np.ndarray], int]:
    """
    Load video frames using FFmpeg extraction.
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        frame_paths, fps, _ = _extract_frames_with_ffmpeg(video_path, temp_dir)
        
        frames = []
        for path in frame_paths:
            frame = cv2.imread(path)
            if frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
        
        return frames, fps
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
