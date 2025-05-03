#!/bin/bash
# This script creates a local development environment for testing

# Exit on error
set -e

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is required but not found. Please install Docker."
    exit 1
fi

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is required but not found. Please install AWS CLI."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found. Please install Python 3."
    exit 1
fi

# Start DynamoDB local (requires Docker)
echo "Starting DynamoDB local container..."
docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local

# Create the test table
echo "Creating DynamoDB table..."
aws dynamodb create-table \
    --cli-input-json file://deploy/create_table.json \
    --endpoint-url http://localhost:8000 \
    --region eu-central-1

# Install Python dependencies
echo "Installing Python dependencies..."
cd app
pip3 install -r requirements.txt

# Set environment variables
export DYNAMODB_TABLE="parking-tickets"
export AWS_REGION="eu-central-1" 
export DYNAMODB_LOCAL="true"
export DYNAMODB_ENDPOINT="http://localhost:8000"

# Run the API server
echo "Starting the API server..."
uvicorn main:app --reload

# Note: This script ends when the server is stopped with Ctrl+C

# Define cleanup function
cleanup() {
    echo "Cleaning up resources..."
    docker stop dynamodb-local 2>/dev/null || true
    docker rm dynamodb-local 2>/dev/null || true
    echo "Cleanup complete."
}

# If you want automatic cleanup when the script exits, uncomment the line below
# trap cleanup EXIT

# If you want to manually clean up later, run:
# docker stop dynamodb-local
# docker rm dynamodb-local
