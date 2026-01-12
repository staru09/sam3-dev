# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Video segmentation endpoints for SAM3 API.
"""

import uuid

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from api.core.task_store import task_store
from api.core.worker import worker
from api.models.schemas import BackgroundMode, OutputFormat


router = APIRouter(prefix="/segment", tags=["Segmentation"])


@router.post("/dog")
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
    gcs_bucket: str = Form(
        default="nannie_sam3",
        description="GCS bucket name for output upload"
    ),
):
    """
    Segment dogs from a video stored in GCS and remove the background.
    
    This endpoint returns immediately with a task_id. Use `/poll/{task_id}` 
    to check processing status and get the result.
    
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
    - **gcs_bucket**: GCS bucket name for output (default: nannie_sam3)
    
    **Returns:**
    - **202 Accepted** with task_id for polling
    
    **Example Response:**
    ```json
    {
        "task_id": "abc-123-def-456",
        "status": "queued",
        "message": "Video segmentation job queued",
        "poll_url": "/poll/abc-123-def-456"
    }
    ```
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Create task in store
    task_store.create_task(task_id)
    
    # Enqueue job for background processing
    worker.enqueue(
        task_id=task_id,
        job_params={
            "source_bucket": source_bucket,
            "video_uuid": video_uuid,
            "video_blob_path": video_blob_path,
            "prompt": "dog",
            "background_mode": background_mode.value,
            "include_overlay": include_overlay,
            "gcs_bucket": gcs_bucket,
        }
    )
    
    # Return immediately with 202 Accepted
    return JSONResponse(
        status_code=202,
        content={
            "task_id": task_id,
            "status": "queued",
            "message": "Video segmentation job queued",
            "poll_url": f"/poll/{task_id}"
        }
    )


@router.post("")
async def segment_from_video(
    source_bucket: str = Form(..., description="GCS bucket name containing the input video"),
    video_uuid: str = Form(..., description="UUID of the input video in the source bucket"),
    video_blob_path: str = Form(..., description="Path to video blob in bucket"),
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
    gcs_bucket: str = Form(
        default="nannie_sam3",
        description="GCS bucket name for upload"
    ),
):
    """
    Segment objects from a video using a custom text prompt.
    
    This endpoint returns immediately with a task_id. Use `/poll/{task_id}` 
    to check processing status and get the result.
    
    **Parameters:**
    - **source_bucket**: GCS bucket containing the input video
    - **video_uuid**: UUID of the input video (for reference tracking)
    - **video_blob_path**: Path to the video blob in the source bucket
    - **prompt**: Text describing what to segment (e.g., "dog", "person with red shirt")
    - **background_mode**: How to handle the background
    - **output_format**: Output video format
    - **include_overlay**: Include visualization video
    - **gcs_bucket**: GCS bucket name (default: nannie_sam3)
    
    **Returns:**
    - **202 Accepted** with task_id for polling
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Create task in store
    task_store.create_task(task_id)
    
    # Enqueue job for background processing
    worker.enqueue(
        task_id=task_id,
        job_params={
            "source_bucket": source_bucket,
            "video_uuid": video_uuid,
            "video_blob_path": video_blob_path,
            "prompt": prompt,
            "background_mode": background_mode.value,
            "include_overlay": include_overlay,
            "gcs_bucket": gcs_bucket,
        }
    )
    
    # Return immediately with 202 Accepted
    return JSONResponse(
        status_code=202,
        content={
            "task_id": task_id,
            "status": "queued",
            "message": "Video segmentation job queued",
            "poll_url": f"/poll/{task_id}"
        }
    )
