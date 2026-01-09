# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Video segmentation endpoints for SAM3 API.
"""

from fastapi import APIRouter, File, Form, UploadFile

from api.models.schemas import (
    BackgroundMode,
    OutputFormat,
    VideoSegmentationResponse,
)
from api.handlers.video_processing import (
    process_video_segmentation,
    process_video_from_gcs,
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
    
    This endpoint downloads a video from the specified GCS bucket, 
    extracts dogs from the video, and uploads the output with a new UUID.
    The input video is NOT saved - only the processed output is stored.
    
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
    - Processed video with only the dog(s) visible
    - Optional overlay video for visualization
    """
    return await process_video_from_gcs(
        source_bucket=source_bucket,
        video_uuid=video_uuid,
        video_blob_path=video_blob_path,
        prompt="dog",
        background_mode=background_mode,
        output_format=output_format,
        include_overlay=include_overlay,
        upload_to_gcs=upload_to_gcs,
        gcs_bucket=gcs_bucket,
    )


@router.post("", response_model=VideoSegmentationResponse)
async def segment_from_video(
    video: UploadFile = File(..., description="Video file to process"),
    prompt: str = Form(
        default="dog",
        description="Text prompt describing what to segment"
    ),
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
