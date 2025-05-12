#!/bin/bash
set -eu

DOCKER_IMAGE="aelka/cloud-computing-hw1:latest"

# Build the Docker image
echo "Building Docker image ${DOCKER_IMAGE}..."
docker build -t ${DOCKER_IMAGE} .

# Push to Docker Hub
echo "Pushing image to Docker Hub..."
docker push ${DOCKER_IMAGE}

echo "Image successfully built and pushed: ${DOCKER_IMAGE}"
