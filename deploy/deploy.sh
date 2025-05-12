#!/bin/bash
set -eu

# This script deploys the Parking Lot Management System using AWS CloudFormation.
REGION="eu-central-1"
STACK_NAME="parking-lot-system"
STAGE="dev"
INSTANCE_TYPE="t2.micro"
DOCKER_IMAGE="aelka/cloud-computing-hw1:latest"
SSH_LOCATION=$(curl -s https://checkip.amazonaws.com)/32  # Auto-detect current IP for SSH access

# Check required parameters
if [ -z "$KEY_PAIR_NAME" ]; then
    echo "Error: KEY_PAIR_NAME environment variable is not set."
    echo "Please set it with: export KEY_PAIR_NAME=your-key-pair-name"
    exit 1
fi

echo "====== Deploying Parking Lot Management System ======"
echo "Stack: $STACK_NAME | Region: $REGION | Stage: $STAGE | Instance: $INSTANCE_TYPE"
echo "Key Pair: $KEY_PAIR_NAME | SSH Access From: $SSH_LOCATION"
echo "Docker Image: $DOCKER_IMAGE"

# Validate requirements
command -v aws &>/dev/null || { echo "Error: AWS CLI is required"; exit 1; }
aws sts get-caller-identity &>/dev/null || { echo "Error: AWS credentials invalid"; exit 1; }

# Deploy CloudFormation stack
echo "Creating CloudFormation stack..."
aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file deploy/template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --parameter-overrides \
      KeyName="$KEY_PAIR_NAME" \
      DockerImage="$DOCKER_IMAGE" \
      Stage="$STAGE" \
      InstanceType="$INSTANCE_TYPE" \
      SSHLocation="$SSH_LOCATION"

echo "Stack creation started, waiting for completion..."

# Wait for stack creation to complete
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $REGION

if [ $? -eq 0 ]; then
    # Get outputs
    INSTANCE_IP=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query "Stacks[0].Outputs[?OutputKey=='ParkingLotInstanceIP'].OutputValue" --output text)
    WEBSITE_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query "Stacks[0].Outputs[?OutputKey=='WebsiteURL'].OutputValue" --output text)
    
    echo "====== Deployment Complete ======"
    echo "EC2 Instance IP: $INSTANCE_IP"
    echo "Application URL: $WEBSITE_URL"
    echo 
    echo "SSH Access: ssh -i \"$KEY_PAIR_NAME.pem\" ubuntu@$INSTANCE_IP"
    echo "Test API: curl $WEBSITE_URL/health"
    echo 
    echo "Clean up: aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
else
    echo "Stack creation failed."
    echo "Check details: aws cloudformation describe-stack-events --stack-name $STACK_NAME --region $REGION"
fi
