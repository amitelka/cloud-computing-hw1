#!/bin/bash
set -e

# This script contains instructions for manually deploying the Parking Lot Management System
# on an EC2 instance manually

echo "====== Manual EC2 Deployment Steps ======"

# 1. Launch Amazon Linux 2023 EC2 Instance
echo "1. Launch an EC2 instance with Amazon Linux 2023 AMI"
echo "   - Instance type: t2.micro (or larger)"
echo "   - Configure security group to allow:"
echo "     - SSH (port 22)"
echo "     - HTTP (port 8000)"
echo "   - Use an existing key pair or create a new one"
echo "   - Attach an IAM role with permissions for DynamoDB"
echo ""
echo "   Latest Amazon Linux 2023 AMI IDs:"
echo "   - eu-central-1: ami-06dd92ecc74fdfb36"
echo "   - eu-west-1: ami-0ab14756db2442499"
echo "   - us-east-1: ami-067d1e60475437da2"
echo "   - us-west-2: ami-04b4d3355239f9d85"
echo ""
echo "   Example AWS CLI command:"
echo "   aws ec2 run-instances \\"
echo "     --image-id ami-06dd92ecc74fdfb36 \\"  # Amazon Linux 2023 in eu-central-1
echo "     --instance-type t2.micro \\"
echo "     --key-name MyKeyPair \\"
echo "     --security-group-ids sg-XXXXXXXX \\"
echo "     --iam-instance-profile Name=ParkingLotRole \\"  # Optional: IAM role with DynamoDB permissions
echo "     --user-data file://user-data.sh \\"
echo "     --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=parking-lot-system}]'"
echo ""

# 2. Connect to the instance
echo "2. Connect to the EC2 instance once it's running:"
echo "   ssh -i your-key.pem ec2-user@your-instance-public-ip"
echo ""

# 3. Setup instructions
echo "3. Set up the application:"
echo "   # Install git if needed"
echo "   sudo yum install -y git"
echo ""
echo "   # Clone the repository"
echo "   git clone https://github.com/your-username/parking-lot-system.git"
echo "   cd parking-lot-system"
echo ""
echo "   # Run the setup script"
echo "   cd deploy"
echo "   chmod +x ec2_setup.sh"
echo "   sudo ./ec2_setup.sh"
echo ""

# 4. Testing the deployment
echo "4. Test the deployment:"
echo "   # Check if service is running"
echo "   sudo systemctl status parking-lot"
echo ""
echo "   # Test the API"
echo "   curl http://localhost:8000/health"
echo ""
echo "   # Create a parking ticket"
echo "   curl -X POST http://localhost:8000/entry \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"license_plate\": \"AB-1234\"}'"
echo ""

# 5. Monitoring and Troubleshooting
echo "5. Monitoring and Troubleshooting:"
echo "   # View service logs"
echo "   sudo journalctl -u parking-lot"
echo ""
echo "   # Check application logs"
echo "   sudo journalctl -u parking-lot | grep -i error"
echo ""
echo "   # Restart service if needed"
echo "   sudo systemctl restart parking-lot"
echo ""
echo "   # Monitor DynamoDB table"
echo "   aws dynamodb scan --table-name parking-tickets --region eu-central-1 --output json"
echo ""

# 6. Cleanup instructions
echo "6. Cleanup when finished:"
echo "   # Stop the service"
echo "   sudo systemctl stop parking-lot"
echo "   sudo systemctl disable parking-lot"
echo ""
echo "   # Delete the DynamoDB table"
echo "   aws dynamodb delete-table --table-name parking-tickets --region eu-central-1"
echo ""
echo "   # Terminate the EC2 instance (from your local machine)"
echo "   aws ec2 terminate-instances --instance-ids i-XXXXXXXXXXXXXXXXX --region eu-central-1"

echo "====== End of Manual EC2 Deployment Steps ======"
