# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Video processing handlers for SAM3 API.
Contains the core business logic for video segmentation.
"""

import functools
import asyncio
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from api.core.config import OUTPUT_DIR, PROCESSED_VIDEOS_DIR, ALLOWED_VIDEO_EXTENSIONS, task_store
from api.models.schemas import BackgroundMode, OutputFormat, VideoSegmentationResponse
from api.services.sam3_service import sam3_service


async def process_video_segmentation(
    video: UploadFile,
    prompt: str,
    background_mode: BackgroundMode,
    output_format: OutputFormat,
    include_overlay: bool,
    upload_to_gcs: bool = True,
    gcs_bucket: str = "nannie_sam3",
) -> VideoSegmentationResponse:
    """
    Process video segmentation from uploaded file.
    Saves both input and output videos with a generated UUID.
    """
    # Validate file type
    if not video.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_ext = Path(video.filename).suffix.lower()
    if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )
    
    # Ensure model is loaded
    if not sam3_service.is_loaded:
        try:
            sam3_service.load_model()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to load SAM3 model: {str(e)}"
            )
    
    # Create unique task ID and directories
    task_id = str(uuid.uuid4())
    task_output_dir = OUTPUT_DIR / task_id
    task_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded video
    input_video_path = task_output_dir / f"input{file_ext}"
    try:
        with open(input_video_path, "wb") as f:
            content = await video.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded video: {str(e)}"
        )
    
    try:
        # Process video
        result = sam3_service.segment_video(
            video_path=str(input_video_path),
            prompt=prompt,
            background_mode=background_mode.value,
            output_dir=str(task_output_dir),
            include_overlay=include_overlay,
        )
        
        # Build response
        output_video_path = None
        overlay_video_path = None
        gcs_urls = []
        
        if result["output_video_path"]:
            # Move to final destination
            PROCESSED_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
            final_output_path = PROCESSED_VIDEOS_DIR / f"{task_id}.mp4"
            shutil.move(result["output_video_path"], final_output_path)
            
            output_video_path = f"/datacam_videos/processed_videos/{task_id}.mp4"
            
            # Upload to GCS if requested
            if upload_to_gcs:
                try:
                    from api.utils.gcs_utils import upload_to_gcs as gcs_upload
                    gcs_url = gcs_upload(
                        local_path=str(final_output_path),
                        bucket_name=gcs_bucket,
                        destination_blob_name=f"outputs/{task_id}/{task_id}.mp4"
                    )
                    gcs_urls.append(gcs_url)
                    print(f"Uploaded to GCS: {gcs_url}")
                except Exception as e:
                    print(f"Warning: Failed to upload to GCS: {e}")
        
        if result["overlay_video_path"]:
            overlay_video_path = f"/outputs/{task_id}/{Path(result['overlay_video_path']).name}"
            
            # Upload overlay to GCS if requested
            if upload_to_gcs:
                try:
                    from api.utils.gcs_utils import upload_to_gcs as gcs_upload
                    gcs_url = gcs_upload(
                        local_path=result["overlay_video_path"],
                        bucket_name=gcs_bucket,
                        destination_blob_name=f"outputs/{task_id}/{Path(result['overlay_video_path']).name}"
                    )
                    gcs_urls.append(gcs_url)
                    print(f"Uploaded overlay to GCS: {gcs_url}")
                except Exception as e:
                    print(f"Warning: Failed to upload overlay to GCS: {e}")
        
        response_message = result["message"]
        if gcs_urls:
            response_message += f" GCS URLs: {', '.join(gcs_urls)}"
        
        return VideoSegmentationResponse(
            success=result["success"],
            message=response_message,
            output_video_path=output_video_path,
            overlay_video_path=overlay_video_path,
            total_frames=result["total_frames"],
            objects_detected=result["objects_detected"],
            processing_time_seconds=result["processing_time_seconds"],
        )
        
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(task_output_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing video: {str(e)}"
        )


async def process_video_from_gcs_async(
    source_bucket: str,
    video_uuid: str,
    video_blob_path: str,
    prompt: str,
    background_mode: BackgroundMode,
    output_format: OutputFormat,
    include_overlay: bool,
    upload_to_gcs: bool = True,
    gcs_bucket: str = "nannie_sam3",
    task_id: str = None,
) -> VideoSegmentationResponse:
    """
    Process video from GCS bucket asynchronously with task tracking and automatic cleanup.
    This version is used for /segment/dog endpoint which queues tasks and cleans up after completion.
    """
    try:
        from api.utils.gcs_utils import download_from_gcs, upload_to_gcs as gcs_upload
    except ImportError as e:
        error_msg = (
            f"Failed to import Google Cloud Storage utilities: {e}\n"
            "Please install google-cloud-storage:\n"
            "  pip install google-cloud-storage\n"
            "Or install all API requirements:\n"
            "  pip install -r requirements-api.txt"
        )
        task_store[task_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": error_msg
        }
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
    
    # Validate blob path extension
    file_ext = Path(video_blob_path).suffix.lower()
    if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
        task_store[task_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        }
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )
    
    # Ensure model is loaded
    if not sam3_service.is_loaded:
        try:
            sam3_service.load_model()
        except Exception as e:
            task_store[task_id] = {
                "status": "failed",
                "progress": 0.0,
                "message": f"Failed to load SAM3 model: {str(e)}"
            }
            raise HTTPException(
                status_code=503,
                detail=f"Failed to load SAM3 model: {str(e)}"
            )
    
    # Update task status
    task_store[task_id] = {
        "status": "processing",
        "progress": 0.0,
        "current_frame": 0,
        "total_frames": 0,
        "message": "Downloading video from GCS..."
    }
    
    # Generate NEW unique task ID for output (different from input video_uuid)
    output_task_id = task_id
    task_output_dir = OUTPUT_DIR / output_task_id
    task_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for input video (will be cleaned up after processing)
    temp_input_dir = task_output_dir / "temp_input"
    temp_input_dir.mkdir(parents=True, exist_ok=True)
    input_video_path = temp_input_dir / f"input{file_ext}"
    
    try:
        # Download video from GCS
        print(f"Downloading video from gs://{source_bucket}/{video_blob_path}")
        download_from_gcs(
            bucket_name=source_bucket,
            source_blob_name=video_blob_path,
            destination_path=str(input_video_path)
        )
        print(f"Video downloaded to {input_video_path}")
        
        # Update progress
        task_store[task_id]["progress"] = 0.1
        task_store[task_id]["message"] = "Processing video..."
        
    except Exception as e:
        shutil.rmtree(task_output_dir, ignore_errors=True)
        task_store[task_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"Failed to download video from GCS: {str(e)}"
        }
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download video from GCS: {str(e)}"
        )
    
    try:
        # Process video with progress callback
        def progress_callback(message, progress, current_frame, total_frames):
            task_store[task_id].update({
                "status": "processing",
                "progress": progress,
                "current_frame": current_frame,
                "total_frames": total_frames,
                "message": message
            })
        
        # Run blocking segmentation in a thread to avoid blocking the event loop
        # We use functools.partial to pass keyword arguments cleanly
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,  # Use default executor
            functools.partial(
                sam3_service.segment_video,
                video_path=str(input_video_path),
                prompt=prompt,
                background_mode=background_mode.value,
                output_dir=str(task_output_dir),
                include_overlay=include_overlay,
                progress_callback=progress_callback,
            )
        )
        
        # Clean up temp input directory (we don't save input video)
        shutil.rmtree(temp_input_dir, ignore_errors=True)
        
        # Build response
        output_video_path = None
        overlay_video_path = None
        gcs_urls = []
        
        task_store[task_id]["progress"] = 0.9
        task_store[task_id]["message"] = "Uploading to GCS..."
        
        if result["output_video_path"]:
            # Move to final destination
            PROCESSED_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
            final_output_path = PROCESSED_VIDEOS_DIR / f"{output_task_id}.mp4"
            shutil.move(result["output_video_path"], final_output_path)
            
            output_video_path = f"/datacam_videos/processed_videos/{output_task_id}.mp4"
            
            # Upload to GCS if requested
            if upload_to_gcs:
                try:
                    gcs_url = gcs_upload(
                        local_path=str(final_output_path),
                        bucket_name=gcs_bucket,
                        destination_blob_name=f"outputs/{output_task_id}/{output_task_id}.mp4"
                    )
                    gcs_urls.append(gcs_url)
                    print(f"Uploaded to GCS: {gcs_url}")
                except Exception as e:
                    print(f"Warning: Failed to upload to GCS: {e}")
        
        if result["overlay_video_path"]:
            overlay_video_path = f"/outputs/{output_task_id}/{Path(result['overlay_video_path']).name}"
            
            # Upload overlay to GCS if requested
            if upload_to_gcs:
                try:
                    gcs_url = gcs_upload(
                        local_path=result["overlay_video_path"],
                        bucket_name=gcs_bucket,
                        destination_blob_name=f"outputs/{output_task_id}/{Path(result['overlay_video_path']).name}"
                    )
                    gcs_urls.append(gcs_url)
                    print(f"Uploaded overlay to GCS: {gcs_url}")
                except Exception as e:
                    print(f"Warning: Failed to upload overlay to GCS: {e}")
        
        response_message = result["message"]
        response_message += f" Input UUID: {video_uuid}, Output UUID: {output_task_id}"
        if gcs_urls:
            response_message += f" GCS URLs: {', '.join(gcs_urls)}"
        
        # Update task as completed
        task_store[task_id] = {
            "status": "completed",
            "progress": 1.0,
            "current_frame": result["total_frames"],
            "total_frames": result["total_frames"],
            "message": response_message,
            "result": {
                "success": result["success"],
                "output_video_path": output_video_path,
                "overlay_video_path": overlay_video_path,
                "objects_detected": result["objects_detected"],
                "processing_time_seconds": result["processing_time_seconds"],
            }
        }
        
        # Cleanup local files after successful processing and GCS upload
        try:
            shutil.rmtree(task_output_dir, ignore_errors=True)
            print(f"Cleaned up local files for task {task_id}")
        except Exception as e:
            print(f"Warning: Failed to cleanup local files: {e}")
        
        return VideoSegmentationResponse(
            success=result["success"],
            message=response_message,
            task_id=task_id,
            output_video_path=output_video_path,
            overlay_video_path=overlay_video_path,
            total_frames=result["total_frames"],
            objects_detected=result["objects_detected"],
            processing_time_seconds=result["processing_time_seconds"],
        )
        
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(task_output_dir, ignore_errors=True)
        task_store[task_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"Error processing video: {str(e)}"
        }
        raise HTTPException(
            status_code=500,
            detail=f"Error processing video: {str(e)}"
        )


async def process_video_from_gcs(
    source_bucket: str,
    video_uuid: str,
    video_blob_path: str,
    prompt: str,
    background_mode: BackgroundMode,
    output_format: OutputFormat,
    include_overlay: bool,
    upload_to_gcs: bool = True,
    gcs_bucket: str = "nannie_sam3",
) -> VideoSegmentationResponse:
    """
    Process video from GCS bucket.
    Downloads video from source bucket, processes it, and uploads output with new UUID.
    Input video is NOT saved - only output is stored.
    
    Args:
        source_bucket: GCS bucket containing source video
        video_uuid: UUID of the input video (for reference/tracking)
        video_blob_path: Path to video blob in source bucket
        prompt: Text prompt for segmentation
        background_mode: Background handling mode
        output_format: Output video format
        include_overlay: Include overlay visualization
        upload_to_gcs: Whether to upload results to GCS
        gcs_bucket: Destination GCS bucket for outputs
    """
    from api.utils.gcs_utils import download_from_gcs, upload_to_gcs as gcs_upload
    
    # Validate blob path extension
    file_ext = Path(video_blob_path).suffix.lower()
    if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )
    
    # Ensure model is loaded
    if not sam3_service.is_loaded:
        try:
            sam3_service.load_model()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to load SAM3 model: {str(e)}"
            )
    
    # Generate NEW unique task ID for output (different from input video_uuid)
    output_task_id = str(uuid.uuid4())
    task_output_dir = OUTPUT_DIR / output_task_id
    task_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for input video (will be cleaned up after processing)
    temp_input_dir = task_output_dir / "temp_input"
    temp_input_dir.mkdir(parents=True, exist_ok=True)
    input_video_path = temp_input_dir / f"input{file_ext}"
    
    try:
        # Download video from GCS
        print(f"Downloading video from gs://{source_bucket}/{video_blob_path}")
        download_from_gcs(
            bucket_name=source_bucket,
            source_blob_name=video_blob_path,
            destination_path=str(input_video_path)
        )
        print(f"Video downloaded to {input_video_path}")
        
    except Exception as e:
        shutil.rmtree(task_output_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download video from GCS: {str(e)}"
        )
    
    try:
        # Process video
        result = sam3_service.segment_video(
            video_path=str(input_video_path),
            prompt=prompt,
            background_mode=background_mode.value,
            output_dir=str(task_output_dir),
            include_overlay=include_overlay,
        )
        
        # Clean up temp input directory (we don't save input video)
        shutil.rmtree(temp_input_dir, ignore_errors=True)
        
        # Build response
        output_video_path = None
        overlay_video_path = None
        gcs_urls = []
        
        if result["output_video_path"]:
            # Move to final destination
            PROCESSED_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
            final_output_path = PROCESSED_VIDEOS_DIR / f"{output_task_id}.mp4"
            shutil.move(result["output_video_path"], final_output_path)
            
            output_video_path = f"/datacam_videos/processed_videos/{output_task_id}.mp4"
            
            # Upload to GCS if requested
            if upload_to_gcs:
                try:
                    gcs_url = gcs_upload(
                        local_path=str(final_output_path),
                        bucket_name=gcs_bucket,
                        destination_blob_name=f"outputs/{output_task_id}/{output_task_id}.mp4"
                    )
                    gcs_urls.append(gcs_url)
                    print(f"Uploaded to GCS: {gcs_url}")
                except Exception as e:
                    print(f"Warning: Failed to upload to GCS: {e}")
        
        if result["overlay_video_path"]:
            overlay_video_path = f"/outputs/{output_task_id}/{Path(result['overlay_video_path']).name}"
            
            # Upload overlay to GCS if requested
            if upload_to_gcs:
                try:
                    gcs_url = gcs_upload(
                        local_path=result["overlay_video_path"],
                        bucket_name=gcs_bucket,
                        destination_blob_name=f"outputs/{output_task_id}/{Path(result['overlay_video_path']).name}"
                    )
                    gcs_urls.append(gcs_url)
                    print(f"Uploaded overlay to GCS: {gcs_url}")
                except Exception as e:
                    print(f"Warning: Failed to upload overlay to GCS: {e}")
        
        response_message = result["message"]
        response_message += f" Input UUID: {video_uuid}, Output UUID: {output_task_id}"
        if gcs_urls:
            response_message += f" GCS URLs: {', '.join(gcs_urls)}"
        
        return VideoSegmentationResponse(
            success=result["success"],
            message=response_message,
            output_video_path=output_video_path,
            overlay_video_path=overlay_video_path,
            total_frames=result["total_frames"],
            objects_detected=result["objects_detected"],
            processing_time_seconds=result["processing_time_seconds"],
        )
        
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(task_output_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing video: {str(e)}"
        )
