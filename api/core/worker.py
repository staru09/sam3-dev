# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Background worker for async video processing.
"""

import shutil
import threading
import time
import uuid
from pathlib import Path
from queue import Queue
from typing import Any, Callable, Dict, Optional

from api.core.config import OUTPUT_DIR, ALLOWED_VIDEO_EXTENSIONS
from api.core.task_store import task_store, TaskStatus


class BackgroundWorker:
    """
    Background worker that processes video segmentation jobs from a queue.
    Runs in a separate thread to avoid blocking the main API.
    """
    
    def __init__(self):
        self._queue: Queue = Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """Start the background worker thread"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
        print("Background worker started")
    
    def stop(self):
        """Stop the background worker thread"""
        self._running = False
        self._queue.put(None)  # Signal to stop
        if self._thread:
            self._thread.join(timeout=5)
        print("Background worker stopped")
    
    def enqueue(self, task_id: str, job_params: Dict[str, Any]):
        """Add a job to the processing queue"""
        self._queue.put((task_id, job_params))
        print(f"Task {task_id} enqueued for processing")
    
    def _process_queue(self):
        """Main loop that processes jobs from the queue"""
        while self._running:
            try:
                item = self._queue.get()
                
                if item is None:
                    break
                
                task_id, job_params = item
                self._process_job(task_id, job_params)
                
            except Exception as e:
                print(f"Error in worker loop: {e}")
    
    def _process_job(self, task_id: str, job_params: Dict[str, Any]):
        """Process a single video segmentation job"""
        from api.services.sam3_service import sam3_service
        from api.utils.gcs_utils import download_from_gcs, upload_to_gcs
        from api.utils.video_utils import (
            apply_mask_to_frame,
            combine_masks,
            create_video_from_frames,
            create_video_with_alpha,
            extract_frames_from_video,
            load_video_frames,
        )
        import numpy as np
        import tempfile
        import gc
        import torch
        
        # Update status to running
        task_store.update_task(
            task_id,
            status=TaskStatus.RUNNING,
            started_at=time.time(),
            message="Starting video processing"
        )
        
        # Extract params
        source_bucket = job_params.get("source_bucket")
        video_blob_path = job_params.get("video_blob_path")
        video_uuid = job_params.get("video_uuid")
        prompt = job_params.get("prompt", "dog")
        background_mode = job_params.get("background_mode", "transparent")
        include_overlay = job_params.get("include_overlay", False)
        gcs_bucket = job_params.get("gcs_bucket", "nannie_sam3")
        
        # Setup directories
        task_output_dir = OUTPUT_DIR / task_id
        task_output_dir.mkdir(parents=True, exist_ok=True)
        temp_input_dir = task_output_dir / "temp_input"
        temp_input_dir.mkdir(parents=True, exist_ok=True)
        
        file_ext = Path(video_blob_path).suffix.lower()
        input_video_path = temp_input_dir / f"input{file_ext}"
        
        try:
            # Download video from GCS
            task_store.update_task(task_id, message="Downloading video from GCS")
            print(f"[{task_id}] Downloading from gs://{source_bucket}/{video_blob_path}")
            download_from_gcs(
                bucket_name=source_bucket,
                source_blob_name=video_blob_path,
                destination_path=str(input_video_path)
            )
            
            # Ensure model is loaded
            if not sam3_service.is_loaded:
                task_store.update_task(task_id, message="Loading SAM3 model")
                sam3_service.load_model()
            
            # Create temp directory for frames
            temp_frames_dir = tempfile.mkdtemp(prefix="sam3_frames_")
            
            try:
                # Extract frames
                task_store.update_task(task_id, message="Extracting video frames", progress=0.05)
                frame_paths, fps, (width, height) = extract_frames_from_video(
                    str(input_video_path), temp_frames_dir
                )
                total_frames = len(frame_paths)
                task_store.update_task(task_id, total_frames=total_frames)
                
                # Start SAM3 session
                task_store.update_task(task_id, message="Starting SAM3 session", progress=0.1)
                response = sam3_service._predictor.handle_request(
                    request=dict(
                        type="start_session",
                        resource_path=temp_frames_dir,
                    )
                )
                session_id = response["session_id"]
                
                try:
                    # Add text prompt
                    task_store.update_task(task_id, message=f"Adding prompt: '{prompt}'")
                    response = sam3_service._predictor.handle_request(
                        request=dict(
                            type="add_prompt",
                            session_id=session_id,
                            frame_index=0,
                            text=prompt,
                        )
                    )
                    
                    initial_output = response["outputs"]
                    objects_detected = len(initial_output.get("out_obj_ids", []))
                    
                    if objects_detected == 0:
                        task_store.update_task(
                            task_id,
                            status=TaskStatus.COMPLETED,
                            completed_at=time.time(),
                            progress=1.0,
                            message=f"No objects matching '{prompt}' detected",
                            result={
                                "success": False,
                                "objects_detected": 0,
                                "gcs_urls": []
                            }
                        )
                        return
                    
                    # Propagate through video
                    task_store.update_task(task_id, message="Propagating segmentation")
                    outputs_per_frame = {}
                    for response in sam3_service._predictor.handle_stream_request(
                        request=dict(
                            type="propagate_in_video",
                            session_id=session_id,
                        )
                    ):
                        frame_idx = response["frame_index"]
                        outputs_per_frame[frame_idx] = response["outputs"]
                        progress = 0.15 + (0.5 * (frame_idx + 1) / total_frames)
                        task_store.update_task(
                            task_id,
                            current_frame=frame_idx + 1,
                            progress=progress,
                            message=f"Processing frame {frame_idx + 1}/{total_frames}"
                        )
                    
                    # Apply masks
                    task_store.update_task(task_id, message="Applying masks to frames", progress=0.7)
                    processed_frames = []
                    overlay_frames = []
                    video_frames, _ = load_video_frames(str(input_video_path))
                    
                    for frame_idx in sorted(outputs_per_frame.keys()):
                        frame = video_frames[frame_idx]
                        output = outputs_per_frame[frame_idx]
                        masks = output.get("out_binary_masks", [])
                        
                        if len(masks) > 0:
                            combined_mask = combine_masks(list(masks))
                            processed_frame = apply_mask_to_frame(
                                frame, combined_mask, background_mode
                            )
                            processed_frames.append(processed_frame)
                            
                            if include_overlay:
                                overlay = sam3_service._create_overlay_frame(
                                    frame, masks, output.get("out_obj_ids", [])
                                )
                                overlay_frames.append(overlay)
                        else:
                            if background_mode == "transparent":
                                alpha = np.zeros((*frame.shape[:2], 1), dtype=np.uint8)
                                processed_frames.append(np.dstack([frame, alpha]))
                            else:
                                bg_frame = apply_mask_to_frame(
                                    frame,
                                    np.zeros(frame.shape[:2], dtype=np.uint8),
                                    background_mode
                                )
                                processed_frames.append(bg_frame)
                            
                            if include_overlay:
                                overlay_frames.append(frame)
                    
                    # Create output video
                    task_store.update_task(task_id, message="Creating output video", progress=0.85)
                    has_alpha = background_mode == "transparent"
                    output_ext = ".webm" if has_alpha else ".mp4"
                    output_video_path = str(task_output_dir / f"segmented{output_ext}")
                    
                    if has_alpha:
                        create_video_with_alpha(processed_frames, output_video_path, fps)
                    else:
                        create_video_from_frames(processed_frames, output_video_path, fps)
                    
                    # Create overlay if requested
                    overlay_video_path = None
                    if include_overlay and overlay_frames:
                        overlay_video_path = str(task_output_dir / "overlay.mp4")
                        create_video_from_frames(overlay_frames, overlay_video_path, fps)
                    
                    # Upload to GCS
                    task_store.update_task(task_id, message="Uploading to GCS", progress=0.9)
                    gcs_urls = []
                    
                    output_blob_name = f"outputs/{task_id}/segmented{output_ext}"
                    gcs_url = upload_to_gcs(
                        local_path=output_video_path,
                        bucket_name=gcs_bucket,
                        destination_blob_name=output_blob_name
                    )
                    gcs_urls.append(gcs_url)
                    print(f"[{task_id}] Uploaded to GCS: {gcs_url}")
                    
                    if overlay_video_path:
                        overlay_blob_name = f"outputs/{task_id}/overlay.mp4"
                        overlay_gcs_url = upload_to_gcs(
                            local_path=overlay_video_path,
                            bucket_name=gcs_bucket,
                            destination_blob_name=overlay_blob_name
                        )
                        gcs_urls.append(overlay_gcs_url)
                    
                    # Mark as completed
                    task_store.update_task(
                        task_id,
                        status=TaskStatus.COMPLETED,
                        completed_at=time.time(),
                        progress=1.0,
                        message=f"Successfully segmented {objects_detected} object(s)",
                        result={
                            "success": True,
                            "objects_detected": objects_detected,
                            "total_frames": total_frames,
                            "input_uuid": video_uuid,
                            "output_uuid": task_id,
                            "gcs_urls": gcs_urls
                        }
                    )
                    
                finally:
                    # Close SAM3 session
                    sam3_service._predictor.handle_request(
                        request=dict(
                            type="close_session",
                            session_id=session_id,
                        )
                    )
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            
            finally:
                # Cleanup temp frames
                shutil.rmtree(temp_frames_dir, ignore_errors=True)
        
        except Exception as e:
            print(f"[{task_id}] Error: {e}")
            task_store.update_task(
                task_id,
                status=TaskStatus.FAILED,
                completed_at=time.time(),
                error=str(e),
                message=f"Processing failed: {str(e)}"
            )
        
        finally:
            # Auto-cleanup local files
            shutil.rmtree(task_output_dir, ignore_errors=True)
            print(f"[{task_id}] Local files cleaned up")


# Global worker instance
worker = BackgroundWorker()
