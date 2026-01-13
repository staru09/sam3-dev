# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

"""
Google Cloud Storage utilities for SAM3 API
"""

import os
from typing import Optional

try:
    from google.cloud import storage
except ImportError:
    raise ImportError(
        "google-cloud-storage is not installed. "
        "Please install it with: pip install google-cloud-storage\n"
        "Or install all API requirements: pip install -r requirements-api.txt"
    )


def upload_to_gcs(
    local_path: str,
    bucket_name: str,
    destination_blob_name: Optional[str] = None,
    project_id: Optional[str] = None
) -> str:
    """
    Upload a file to Google Cloud Storage.
    
    Args:
        local_path: Path to local file to upload
        bucket_name: Name of the GCS bucket (without gs:// prefix)
        destination_blob_name: Destination path in bucket (if None, uses basename)
        project_id: GCP project ID (if None, uses default from environment)
    
    Returns:
        Public URL of the uploaded file
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file not found: {local_path}")
    
    # Get project ID from environment if not provided
    if project_id is None:
        project_id = os.environ.get("PROJECT_ID")
    
    # Initialize GCS client
    if project_id:
        storage_client = storage.Client(project=project_id)
    else:
        storage_client = storage.Client()
    
    # Get bucket
    bucket = storage_client.bucket(bucket_name)
    
    # Determine destination name
    if destination_blob_name is None:
        destination_blob_name = os.path.basename(local_path)
    
    # Upload file
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path)
    
    # Return GCS URL
    return f"gs://{bucket_name}/{destination_blob_name}"


def download_from_gcs(
    bucket_name: str,
    source_blob_name: str,
    destination_path: str,
    project_id: Optional[str] = None
) -> str:
    """
    Download a file from Google Cloud Storage.
    
    Args:
        bucket_name: Name of the GCS bucket (without gs:// prefix)
        source_blob_name: Source path/name of the blob in the bucket
        destination_path: Local path where file should be saved
        project_id: GCP project ID (if None, uses default from environment)
    
    Returns:
        Path to the downloaded file
    """
    # Get project ID from environment if not provided
    if project_id is None:
        project_id = os.environ.get("PROJECT_ID")
    
    # Initialize GCS client
    if project_id:
        storage_client = storage.Client(project=project_id)
    else:
        storage_client = storage.Client()
    
    # Get bucket and blob
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    
    # Create parent directory if it doesn't exist
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    
    # Download file
    blob.download_to_filename(destination_path)
    
    return destination_path


def upload_directory_to_gcs(
    local_directory: str,
    bucket_name: str,
    destination_prefix: str = "",
    project_id: Optional[str] = None
) -> list:
    """
    Upload all files in a directory to GCS.
    
    Args:
        local_directory: Path to local directory
        bucket_name: Name of the GCS bucket
        destination_prefix: Prefix for destination paths in bucket
        project_id: GCP project ID
    
    Returns:
        List of GCS URLs for uploaded files
    """
    if not os.path.isdir(local_directory):
        raise NotADirectoryError(f"Directory not found: {local_directory}")
    
    uploaded_files = []
    
    for filename in os.listdir(local_directory):
        file_path = os.path.join(local_directory, filename)
        if os.path.isfile(file_path):
            destination = f"{destination_prefix}/{filename}" if destination_prefix else filename
            gcs_url = upload_to_gcs(
                local_path=file_path,
                bucket_name=bucket_name,
                destination_blob_name=destination,
                project_id=project_id
            )
            uploaded_files.append(gcs_url)
    
    return uploaded_files
