# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Video segmentation endpoints for SAM3 API.
"""

import asyncio
import uuid

from fastapi import APIRouter, File, Form, UploadFile

from api.core.config import task_store
from api.models.schemas import (
    BackgroundMode,
    OutputFormat,
    VideoSegmentationResponse,
)
from api.handlers.video_processing import (
    process_video_segmentation,
    process_video_from_gcs,
    process_video_from_gcs_async,
)


router = APIRouter(prefix="/segment", tags=["Segmentation"])


@router.post("/dog", response_model=VideoSegmentationResponse)
async def segment_dog_from_video(
    source_bucket: str = Form(..., description="GCS bucket name containing the input video"),
    video_uuid: str = Form(..., description="UUID of the input video in the source bucket"),
    video_blob_path: str = Form(..., description="Path to video blob in bucket (e.g., 'videos/input.mp4')"),
    background_mode: BackgroundMode = Form(
        default=BackgroundMode.TRANSPARENT,
        description="Background removal mode"
    ),
    output_format: OutputFormat = Form(
        default=OutputFormat.MP4,
        description="Output video format"
    ),
    include_overlay: bool = Form(
        default=False,
        description="Include overlay visualization"
    ),
    upload_to_gcs: bool = Form(
        default=True,
        description="Upload results to GCS bucket"
    ),
    gcs_bucket: str = Form(
        default="nannie_sam3",
        description="GCS bucket name for output upload"
    ),
):
    """
    Segment dogs from a video stored in GCS and remove the background.
    
    This endpoint queues the task and returns immediately with a task_id.
    Use the /poll/{task_id} endpoint to check progress.
    The task will automatically cleanup local files after processing and GCS upload.
    
    **Parameters:**
    - **source_bucket**: GCS bucket containing the input video
    - **video_uuid**: UUID of the input video (for reference tracking)
    - **video_blob_path**: Path to the video blob in the source bucket
    - **background_mode**: How to handle the background
        - `transparent`: RGBA with transparent background (requires WebM format)
        - `black`: Solid black background
        - `white`: Solid white background  
        - `blur`: Blurred version of the original background
    - **output_format**: Output video format (mp4, webm, mov)
    - **include_overlay**: Include a visualization video with colored mask overlay
    - **upload_to_gcs**: Upload results to Google Cloud Storage
    - **gcs_bucket**: GCS bucket name for output (default: nannie_sam3)
    
    **Returns:**
    - Immediate response with task_id (status: "queued")
    - Use /poll/{task_id} to check progress and get results
    - Local files are automatically cleaned up after processing
    """
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Initialize task in store
    task_store[task_id] = {
        "status": "queued",
        "progress": 0.0,
        "current_frame": 0,
        "total_frames": 0,
        "message": "Task queued"
    }
    
    # Queue background task
    async def run_processing():
        try:
            await process_video_from_gcs_async(
                source_bucket=source_bucket,
                video_uuid=video_uuid,
                video_blob_path=video_blob_path,
                prompt="dog",
                background_mode=background_mode,
                output_format=output_format,
                include_overlay=include_overlay,
                upload_to_gcs=upload_to_gcs,
                gcs_bucket=gcs_bucket,
                task_id=task_id,
            )
        except Exception as e:
            task_store[task_id] = {
                "status": "failed",
                "progress": 0.0,
                "message": f"Error in background processing: {str(e)}"
            }
    
    # Use asyncio.create_task for async background processing
    asyncio.create_task(run_processing())
    
    # Return immediately with task_id
    return VideoSegmentationResponse(
        success=True,
        message="Task queued successfully",
        task_id=task_id,
        output_video_path=None,
        overlay_video_path=None,
        total_frames=0,
        objects_detected=0,
        processing_time_seconds=0.0,
    )


@router.post("", response_model=VideoSegmentationResponse)
async def segment_from_video(
    video: UploadFile = File(..., description="Video file to process"),
    prompt: str = Form(
        default="dog",
        description="Text prompt describing what to segment"
    ),
    background_mode: BackgroundMode = Form(
        default=BackgroundMode.BLACK,
        description="Background removal mode"
    ),
    output_format: OutputFormat = Form(
        default=OutputFormat.MP4,
        description="Output video format"
    ),
    include_overlay: bool = Form(
        default=False,
        description="Include overlay visualization"
    ),
    upload_to_gcs: bool = Form(
        default=True,
        description="Upload results to GCS bucket"
    ),
    gcs_bucket: str = Form(
        default="nannie_sam3",
        description="GCS bucket name for upload"
    ),
):
    """
    Segment objects from a video using a custom text prompt.
    
    Use this endpoint to extract any object you can describe with text.
    For example: "dog", "cat", "person", "car", "bird", etc.
    
    **Parameters:**
    - **video**: The input video file
    - **prompt**: Text describing what to segment (e.g., "dog", "person with red shirt")
    - **background_mode**: How to handle the background
    - **output_format**: Output video format
    - **include_overlay**: Include visualization video
    - **upload_to_gcs**: Upload results to Google Cloud Storage
    - **gcs_bucket**: GCS bucket name (default: nannie_sam3)
    
    **Returns:**
    - Processed video with only the specified object(s) visible
    """
    return await process_video_segmentation(
        video=video,
        prompt=prompt,
        background_mode=background_mode,
        output_format=output_format,
        include_overlay=include_overlay,
        upload_to_gcs=upload_to_gcs,
        gcs_bucket=gcs_bucket,
    )
