# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Poll endpoint for checking task progress.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.core.config import task_store
from api.models.schemas import SegmentationProgressResponse


router = APIRouter(tags=["Poll"])


class PollResponse(BaseModel):
    """Extended response model for polling that includes result data when completed"""
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float  # 0.0 to 1.0
    current_frame: int = 0
    total_frames: int = 0
    message: Optional[str] = None
    result: Optional[dict] = None  # Result data when status is "completed"


@router.get("/poll/{task_id}", response_model=PollResponse)
async def poll_task(task_id: str):
    """
    Poll the progress of a segmentation task.
    
    **Parameters:**
    - **task_id**: The task ID returned from /segment/dog endpoint
    
    **Returns:**
    - Task status, progress, and current frame information
    - When completed, includes result data with output paths and processing details
    """
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task_info = task_store[task_id]
    
    response_data = {
        "task_id": task_id,
        "status": task_info.get("status", "pending"),
        "progress": task_info.get("progress", 0.0),
        "current_frame": task_info.get("current_frame", 0),
        "total_frames": task_info.get("total_frames", 0),
        "message": task_info.get("message"),
    }
    
    # Include result data when task is completed
    if task_info.get("status") == "completed" and "result" in task_info:
        response_data["result"] = task_info["result"]
    
    return PollResponse(**response_data)
