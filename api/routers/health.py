# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Health check endpoints for SAM3 API.
"""

from fastapi import APIRouter

from api.models.schemas import HealthCheckResponse
from api.services.sam3_service import sam3_service


router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "SAM3 Video Segmentation API",
        "version": "1.0.0",
        "description": "Remove backgrounds from videos using SAM3",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Check API health and model status.
    
    Returns GPU availability, model loading status, and CUDA information.
    """
    gpu_info = sam3_service.get_gpu_info()
    
    return HealthCheckResponse(
        status="healthy" if sam3_service.is_loaded else "model_not_loaded",
        gpu_available=gpu_info["gpu_available"],
        model_loaded=sam3_service.is_loaded,
        cuda_version=gpu_info.get("cuda_version"),
        gpu_name=gpu_info.get("gpu_name"),
    )
