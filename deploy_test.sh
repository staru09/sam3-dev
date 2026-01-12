#!/bin/bash

# Quick deployment test script
# Tests deployment locally before pushing to cloud

set -e

echo "SAM3 API - Local Deployment Test"
echo "================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Build Docker image
echo "Building Docker image..."
docker build -t sam3-api:local -f Dockerfile .

echo ""
echo "Build successful!"
echo ""
echo "To test locally:"
echo "  docker run -p 8080:8080 --gpus all sam3-api:local"
echo ""
echo "Then test with:"
echo "  curl http://localhost:8080/health"
echo ""
echo "To push to Google Cloud Run, use:"
echo "  ./deploy_gpu.sh YOUR_PROJECT_ID"
echo ""
