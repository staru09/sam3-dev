# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Routers module for SAM3 API - endpoint definitions organized by domain.
"""

from api.routers.health import router as health_router
from api.routers.segmentation import router as segmentation_router
from api.routers.poll import router as poll_router

__all__ = [
    "health_router",
    "segmentation_router",
    "poll_router",
]
