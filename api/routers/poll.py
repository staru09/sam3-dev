# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Polling endpoint for checking task status.
"""

from fastapi import APIRouter, HTTPException

from api.core.task_store import task_store


router = APIRouter(tags=["Polling"])


@router.get("/poll/{task_id}")
async def poll_task_status(task_id: str):
    """
    Poll for task status and progress.
    
    **Parameters:**
    - **task_id**: The task ID returned from `/segment` or `/segment/dog`
    
    **Returns:**
    - **task_id**: The task identifier
    - **status**: One of `queued`, `running`, `completed`, `failed`
    - **progress**: Progress percentage (0-100)
    - **current_frame**: Current frame being processed
    - **total_frames**: Total frames in the video
    - **message**: Human-readable status message
    - **result**: (Only when completed) Contains `gcs_urls`, `objects_detected`, etc.
    - **error**: (Only when failed) Error message
    
    **Example Response (Running):**
    ```json
    {
        "task_id": "abc-123",
        "status": "running",
        "progress": 45.5,
        "current_frame": 45,
        "total_frames": 100,
        "message": "Processing frame 45/100"
    }
    ```
    
    **Example Response (Completed):**
    ```json
    {
        "task_id": "abc-123",
        "status": "completed",
        "progress": 100,
        "message": "Successfully segmented 1 object(s)",
        "result": {
            "success": true,
            "gcs_urls": ["gs://bucket/outputs/abc-123/segmented.mp4"],
            "objects_detected": 1
        }
    }
    ```
    """
    task = task_store.get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found. It may have expired or never existed."
        )
    
    response = {
        "task_id": task.task_id,
        "status": task.status,
        "progress": round(task.progress * 100, 1),  # Convert to percentage
        "current_frame": task.current_frame,
        "total_frames": task.total_frames,
        "message": task.message,
    }
    
    if task.status == "completed" and task.result:
        response["result"] = task.result
    elif task.status == "failed" and task.error:
        response["error"] = task.error
    
    return response
