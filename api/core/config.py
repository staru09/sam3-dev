# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Configuration and constants for SAM3 API.
"""

from pathlib import Path


# Output directory for processed videos
OUTPUT_DIR = Path("outputs")

# Store for tracking async tasks
task_store: dict = {}

# Default GCS bucket name
DEFAULT_GCS_BUCKET = "nannie_sam3"

# Allowed video extensions
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

# CORS settings
CORS_SETTINGS = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
