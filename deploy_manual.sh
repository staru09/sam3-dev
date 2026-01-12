#!/bin/bash

# Manual deployment script (alternative to cloudbuild.yaml)
# Usage: ./deploy_manual.sh YOUR_PROJECT_ID [REGION] [GPU_TYPE]

set -e

PROJECT_ID=${1:-""}
REGION=${2:-"europe-west4"}
GPU_TYPE=${3:-"nvidia-l4"}

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: ./deploy_manual.sh YOUR_PROJECT_ID [REGION] [GPU_TYPE]"
    echo "Example: ./deploy_manual.sh my-gcp-project europe-west4 nvidia-l4"
    echo ""
    echo "Available GPU types:"
    echo "  - nvidia-l4 (recommended for cost/performance)"
    echo "  - nvidia-a100-80gb (maximum performance)"
    echo "  - nvidia-tesla-t4 (budget option)"
    exit 1
fi

echo "Manual Deployment: SAM3 Video API with GPU"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "GPU Type: $GPU_TYPE"
echo ""

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com

# Create Artifact Registry repository if it doesn't exist
echo "Setting up Artifact Registry..."
gcloud artifacts repositories create sam3 \
    --repository-format=docker \
    --location=$REGION \
    --description="SAM3 Video API Docker images" \
    2>/dev/null || echo "Repository already exists"

# Build Docker image
echo "Building Docker image locally..."
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/sam3/sam3-api:latest -f Dockerfile .

# Configure Docker for Artifact Registry
echo "Configuring Docker authentication..."
gcloud auth configure-docker $REGION-docker.pkg.dev

# Push to Artifact Registry
echo "Pushing to Artifact Registry..."
docker push $REGION-docker.pkg.dev/$PROJECT_ID/sam3/sam3-api:latest

# Deploy to Cloud Run with GPU
echo "Deploying to Cloud Run with GPU ($GPU_TYPE)..."
gcloud run deploy sam3-api-service \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/sam3/sam3-api:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --execution-environment=gen2 \
  --memory=32Gi \
  --cpu=8 \
  --timeout=900 \
  --max-instances=1 \
  --min-instances=0 \
  --gpu=1 \
  --gpu-type=$GPU_TYPE

echo ""
echo "Deployment complete!"
echo ""
echo "Get your service URL:"
echo "  gcloud run services describe sam3-api-service --region=$REGION --format='value(status.url)'"
echo ""
echo "Test the deployment:"
echo "  SERVICE_URL=\$(gcloud run services describe sam3-api-service --region=$REGION --format='value(status.url)')"
echo "  curl \$SERVICE_URL/health"
echo ""
