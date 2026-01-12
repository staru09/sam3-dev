#!/bin/bash

# Deployment script for SAM3 Video API with GPU on Cloud Run
# Usage: ./deploy_gpu.sh YOUR_PROJECT_ID [TAG]

set -e

PROJECT_ID=${1:-""}
TAG=${2:-"latest"}

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: ./deploy_gpu.sh YOUR_PROJECT_ID [TAG]"
    echo "Example: ./deploy_gpu.sh my-gcp-project v1.0"
    exit 1
fi

echo "Deploying SAM3 Video API to Google Cloud Run with GPU"
echo "Project ID: $PROJECT_ID"
echo "Tag: $TAG"
echo ""

# Set project
echo "Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com

# Create Artifact Registry repository if it doesn't exist
echo "Setting up Artifact Registry..."
gcloud artifacts repositories create sam3 \
    --repository-format=docker \
    --location=europe-west4 \
    --description="SAM3 Video API Docker images" \
    2>/dev/null || echo "Repository already exists"

# Build using Cloud Build
echo "Building Docker image with Cloud Build..."
# Ensure TAG has a value (default to 'latest' if empty)
TAG=${TAG:-latest}
gcloud builds submit --config=cloudbuild.yaml --substitutions=_TAG=$TAG

echo ""
echo "Deployment complete!"
echo ""
echo "Your API endpoints will be available at:"
echo "  https://sam3-api-service-<hash>-ew.a.run.app"
echo ""
echo "Get the service URL:"
echo "  gcloud run services describe sam3-api-service --region=europe-west4 --format='value(status.url)'"
echo ""
echo "Test with:"
echo "  curl https://sam3-api-service-<hash>-ew.a.run.app/health"
echo ""
