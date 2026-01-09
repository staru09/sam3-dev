# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Shared FastAPI dependencies for SAM3 API.
"""

from fastapi import HTTPException

from api.services.sam3_service import sam3_service


async def ensure_model_loaded():
    """
    Dependency to ensure SAM3 model is loaded before processing.
    """
    if not sam3_service.is_loaded:
        try:
            sam3_service.load_model()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to load SAM3 model: {str(e)}"
            )
    return sam3_service
