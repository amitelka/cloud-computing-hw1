#!/bin/bash
# Parking Lot Management System - EC2 Setup Script
# This script sets up the Parking Lot Management System on an EC2 instance

# Make script exit on failure and print commands
set -ex

# Load environment variables if present
if [ -f .env ]; then
    source .env
fi

# Load environment variables from profile.d if they exist
if [ -f /etc/profile.d/parking-lot-env.sh ]; then
    source /etc/profile.d/parking-lot-env.sh
fi

# Update system packages
echo "Updating system packages..."
sudo apt update -y

# Install required tools
apt install -y awscli
aws configure set region ${AWS_REGION}

apt install -y python3.11 python3-pip git
# Check for AWS credentials or role
aws sts get-caller-identity &> /dev/null || {
    echo "Error: AWS credentials not configured or invalid."
    echo "Make sure IAM role is attached or credentials are configured."
    exit 1
}

# Default configuration
: ${PORT:=8000}

# check if GIT_REPO_PATH is set
if [ -z "$GIT_REPO_PATH" ]; then
    echo "Error: GIT_REPO_PATH environment variable is not set."
    echo "Please set it with: export GIT_REPO_PATH=/path/to/your/repo"
    exit 1
fi

APP_DIR=${GIT_REPO_PATH}/app
DEPLOYMENT_DIR=${GIT_REPO_PATH}/deploy

echo "===== Setting up Parking Lot Management System ====="
echo "Region: $AWS_REGION"
echo "Table Name: $DYNAMODB_TABLE"
echo "Port: $PORT"
echo "App Directory: $APP_DIR"

# Install Python dependencies
echo "Installing Python dependencies..."
cd $APP_DIR
python3.11 -m pip install -r requirements.txt

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/parking-lot.service > /dev/null << EOF
[Unit]
Description=Parking Lot Management System
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3.11 -m uvicorn main:app --host 0.0.0.0 --port $PORT
Restart=always
Environment=AWS_REGION=$AWS_REGION
Environment=DYNAMODB_TABLE=$DYNAMODB_TABLE
Environment=PORT=$PORT

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
echo "Enabling and starting the service..."
sudo systemctl daemon-reload
sudo systemctl enable parking-lot
sudo systemctl start parking-lot

# Check service status
echo "Checking service status..."
sudo systemctl status parking-lot

echo "===== Parking Lot Management System setup complete ====="
echo "The API is now running on port $PORT"
echo "Remember to configure security groups to allow traffic to port $PORT"
