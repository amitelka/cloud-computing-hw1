#!/bin/bash
# Parking Lot Management System - Deployment Script
set -e  # Exit on error

# Default configuration
STACK_NAME=${STACK_NAME:-parking-lot-system}
REGION=${REGION:-eu-central-1}
STAGE=${STAGE:-dev}
INSTANCE_TYPE=${INSTANCE_TYPE:-t2.micro}
SSH_LOCATION=${SSH_LOCATION:-$(curl -s https://checkip.amazonaws.com)/32}

# Check required parameters
if [ -z "$KEY_PAIR_NAME" ]; then
    echo "Error: KEY_PAIR_NAME environment variable is not set."
    echo "Please set it with: export KEY_PAIR_NAME=your-key-pair-name"
    exit 1
fi

if [ -z "$GIT_REPO_URL" ]; then
    echo "Error: GIT_REPO_URL environment variable is not set."
    echo "Please set it with: export GIT_REPO_URL=https://github.com/your-username/your-repo.git"
    exit 1
fi

echo "====== Deploying Parking Lot Management System ======"
echo "Stack: $STACK_NAME | Region: $REGION | Stage: $STAGE | Instance: $INSTANCE_TYPE"
echo "Key Pair: $KEY_PAIR_NAME | SSH Access: $SSH_LOCATION"
echo "Repository: $GIT_REPO_URL"

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
      GitRepositoryUrl="$GIT_REPO_URL" \
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
