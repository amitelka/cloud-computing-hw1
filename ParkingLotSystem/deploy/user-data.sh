#!/bin/bash
# User data script for EC2 instance automated setup
# This file can be used during EC2 instance creation to automatically set up the application

# Log all output
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting Parking Lot Management System setup..."

# Update system packages
echo "Updating system packages..."
yum update -y

# Install required packages
echo "Installing required packages..."
yum install -y git python311 python311-pip awscli

# Create application directory
echo "Creating application directory..."
mkdir -p /opt/parking-lot-system
chown ec2-user:ec2-user /opt/parking-lot-system

# Setup AWS credentials (you should store these in AWS Secrets Manager or Parameter Store)
# For the exercise, you can pass these as instance metadata
# Or use an IAM role attached to the instance (recommended)

# The following assumes you're using an IAM role
echo "Setting up AWS configuration..."
REGION="eu-central-1"
aws configure set region ${REGION}

# Clone the repository (update with your actual repository URL)
echo "Cloning repository..."
git clone https://github.com/yourusername/parking-lot-system.git /tmp/parking-lot-system

# Alternative: Download from S3 if you've uploaded your code there
# echo "Downloading application from S3..."
# aws s3 cp s3://your-bucket/parking-lot-system.zip /tmp/
# unzip /tmp/parking-lot-system.zip -d /tmp/parking-lot-system

# Set up the application
echo "Setting up the application..."
cd /tmp/parking-lot-system/deploy
chmod +x ec2_setup.sh
./ec2_setup.sh

echo "Setup complete! Check /var/log/user-data.log for details."

# If you encounter issues, you can access the instance and check logs
cat > /opt/parking-lot-system/troubleshooting.txt << EOF
If the application isn't running properly:
1. Check the user-data log: /var/log/user-data.log
2. Check the service status: sudo systemctl status parking-lot
3. View service logs: sudo journalctl -u parking-lot
3. Run: chmod +x ec2_setup.sh
4. Run: sudo ./ec2_setup.sh
EOF

# Create a welcome message
cat > /etc/motd << EOF
=======================================================
Welcome to Parking Lot Management System EC2 Instance!
=======================================================

Application Directory: /opt/parking-lot-system
Setup Instructions: cat /opt/parking-lot-system/setup_instructions.txt

=======================================================
EOF

# Make EC2 instance information available on login
echo "cat /etc/motd" >> /home/ec2-user/.bashrc

echo "EC2 instance setup completed via user data"
