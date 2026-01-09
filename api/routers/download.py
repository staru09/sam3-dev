# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Download endpoints for SAM3 API.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.core.config import OUTPUT_DIR


router = APIRouter(tags=["Download"])


@router.get("/download/{task_id}/{filename}")
async def download_video(task_id: str, filename: str):
    """
    Download a processed video file.
    
    **Parameters:**
    - **task_id**: The task ID from the segmentation response
    - **filename**: The video filename to download
    
    **Returns:**
    - The video file for download
    """
    file_path = OUTPUT_DIR / task_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_type = "video/mp4"
    if filename.endswith(".webm"):
        media_type = "video/webm"
    elif filename.endswith(".mov"):
        media_type = "video/quicktime"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )
