# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Application lifespan handlers for SAM3 API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.core.config import OUTPUT_DIR
from api.services.sam3_service import sam3_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Loads the model on startup and cleans up on shutdown.
    """
    # Startup
    print("=" * 60)
    print("SAM3 Video Segmentation API Starting...")
    print("=" * 60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Load the SAM3 model
    try:
        sam3_service.load_model()
        print("SAM3 model loaded successfully!")
    except Exception as e:
        print(f"Warning: Failed to load SAM3 model on startup: {e}")
        print("Model will be loaded on first request.")
    
    yield
    
    # Shutdown
    print("Shutting down SAM3 service...")
    sam3_service.shutdown()
    print("Cleanup complete.")
