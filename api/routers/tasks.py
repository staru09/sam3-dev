# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Task management endpoints for SAM3 API.
"""

import shutil

from fastapi import APIRouter, HTTPException

from api.core.config import OUTPUT_DIR


router = APIRouter(tags=["Tasks"])


@router.delete("/cleanup/{task_id}")
async def cleanup_task(task_id: str):
    """
    Clean up files for a completed task.
    
    Call this endpoint after downloading the processed video to free up
    server storage.
    
    **Parameters:**
    - **task_id**: The task ID to clean up
    """
    task_dir = OUTPUT_DIR / task_id
    
    if not task_dir.exists():
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        shutil.rmtree(task_dir)
        return {"success": True, "message": f"Task {task_id} cleaned up successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup task: {str(e)}"
        )


@router.get("/tasks")
async def list_tasks():
    """
    List all task directories and their files.
    
    Useful for debugging and monitoring storage usage.
    """
    tasks = []
    
    if OUTPUT_DIR.exists():
        for task_dir in OUTPUT_DIR.iterdir():
            if task_dir.is_dir():
                files = list(task_dir.iterdir())
                tasks.append({
                    "task_id": task_dir.name,
                    "files": [f.name for f in files],
                    "size_mb": sum(f.stat().st_size for f in files) / (1024 * 1024),
                })
    
    return {
        "total_tasks": len(tasks),
        "tasks": tasks,
    }
