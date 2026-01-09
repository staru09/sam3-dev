# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Routers module for SAM3 API - endpoint definitions organized by domain.
"""

from api.routers.health import router as health_router
from api.routers.segmentation import router as segmentation_router
from api.routers.download import router as download_router
from api.routers.tasks import router as tasks_router

__all__ = [
    "health_router",
    "segmentation_router",
    "download_router",
    "tasks_router",
]
