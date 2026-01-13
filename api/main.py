# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
SAM3 Video Segmentation FastAPI Backend

This API provides endpoints for video segmentation using Meta's SAM3 model.
Upload a video and get back a video with only the specified object (e.g., dog)
visible, with the background removed.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.core.config import OUTPUT_DIR, CORS_SETTINGS
from api.core.lifespan import lifespan
from api.routers import (
    health_router,
    segmentation_router,
    poll_router,
)


# Create FastAPI app
app = FastAPI(
    title="SAM3 Video Segmentation API",
    description="""
    ## Video Background Removal with SAM3
    
    This API uses Meta's Segment Anything Model 3 (SAM3) to segment objects from videos
    and remove the background.
    
    ### Features:
    - **Text-based segmentation**: Simply describe what you want to keep (e.g., "dog", "cat", "person")
    - **Multiple background modes**: Transparent, black, white, or blurred background
    - **Multiple output formats**: MP4, WebM (with alpha), MOV
    
    ### Example Usage:
    1. Upload a video with a dog
    2. Set prompt to "dog"
    3. Get back a video with only the dog visible
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(CORSMiddleware, **CORS_SETTINGS)

# Mount static files for serving output videos
OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

# Include routers
app.include_router(health_router)
app.include_router(segmentation_router)
app.include_router(poll_router)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,  # SAM3 requires single worker due to GPU memory
    )
