#!/bin/bash
set -e

# Parking Lot Management System - EC2 Setup Script
# This script sets up the Parking Lot Management System on an EC2 instance

# Make script exit on failure and print commands
set -ex

# Load environment variables if present
if [ -f .env ]; then
    source .env
fi

# Check for required tools
for tool in aws python3 pip3; do
    if ! command -v $tool &> /dev/null; then
        echo "Error: $tool is required but not found. Please install it."
        exit 1
    fi
done

# Check for AWS credentials
aws sts get-caller-identity &> /dev/null || {
    echo "Error: AWS credentials not configured or invalid."
    echo "Please run 'aws configure' to set up your AWS credentials."
    exit 1
}

# Default configuration
: ${REGION:=eu-central-1}
: ${TABLE_NAME:=parking-tickets}
: ${PORT:=8000}
: ${APP_DIR:=/opt/parking-lot-system}

echo "===== Setting up Parking Lot Management System ====="
echo "Region: $REGION"
echo "Table Name: $TABLE_NAME"
echo "Port: $PORT"
echo "App Directory: $APP_DIR"

# Update system packages
echo "Updating system packages..."
sudo yum update -y

# Install Python and required packages
echo "Installing Python and required packages..."
sudo yum install -y python311 python311-pip git

# Create application directory
echo "Creating application directory..."
sudo mkdir -p $APP_DIR
sudo chown ec2-user:ec2-user $APP_DIR

# Copy application files
echo "Copying application files..."
cp -r ../app/* $APP_DIR/

# Install Python dependencies
echo "Installing Python dependencies..."
cd $APP_DIR
pip3.11 install -r requirements.txt

# Create DynamoDB table if it doesn't exist
echo "Creating DynamoDB table if it doesn't exist..."

# Store the script directory to access create_table.json
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

aws dynamodb describe-table --table-name $TABLE_NAME --region $REGION || \
aws dynamodb create-table \
    --cli-input-json file://${SCRIPT_DIR}/create_table.json \
    --region $REGION

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/parking-lot.service > /dev/null << EOF
[Unit]
Description=Parking Lot Management System
After=network.target

[Service]
User=ec2-user
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3.11 -m uvicorn main:app --host 0.0.0.0 --port $PORT
Restart=always
Environment=AWS_REGION=$REGION
Environment=DYNAMODB_TABLE=$TABLE_NAME
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
