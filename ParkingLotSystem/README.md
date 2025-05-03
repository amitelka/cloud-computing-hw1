# Parking Lot Management System

A cloud-based system for managing parking lot entries, exits, and fee calculations, designed for Linux deployment.

## Architecture

This project implements a Parking Lot Management System with the following components:

- **API Server**: Built with FastAPI, handles all parking-related operations
- **Database**: Uses AWS DynamoDB for storing ticket information
- **Deployment**: Amazon Linux 2023 EC2 instance with systemd service
- **Infrastructure as Code**: Uses CloudFormation for resource management

## Features

- **Vehicle Entry**: Create parking tickets with unique IDs
- **Vehicle Exit**: Process payments and calculate fees based on parking duration
- **Fee Calculation**:
  - First 15 min block is always charged
  - Billing unit = 15 min
  - Rate = 2 € per 15 min (8 €/h)
  - Partial blocks are rounded up
  - Daily cap: 40 € per 24h
- **Ticket Queries**: Filter tickets by license plate and status

## Local Setup

### Prerequisites

- Python 3.11
- AWS CLI configured with appropriate permissions
- DynamoDB local (optional for local development)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/parking-lot-system.git
   cd parking-lot-system
   ```

2. Install dependencies:
   ```bash
   cd app
   pip install -r requirements.txt
   ```

3. Run DynamoDB local (optional):
   ```bash
   docker run -p 8000:8000 amazon/dynamodb-local
   ```

4. Create the DynamoDB table:
   ```bash
   aws dynamodb create-table --cli-input-json file://../deploy/create_table.json --endpoint-url http://localhost:8000
   ```

5. Set environment variables:
   ```bash
   export DYNAMODB_TABLE="parking-tickets"
   export AWS_REGION="eu-central-1"
   export DYNAMODB_LOCAL="true"
   export DYNAMODB_ENDPOINT="http://localhost:8000"
   ```

6. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

7. Access the API documentation at http://localhost:8000/docs

### Running Tests

```bash
cd app
pytest ../tests/ -v --cov=.
```

## API Usage Examples

### Create a Parking Ticket (Entry)

```bash
curl -X POST http://localhost:8000/entry \
  -H "Content-Type: application/json" \
  -d '{"license_plate": "AB-1234"}'
```

Example response:
```json
{
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "license_plate": "AB-1234",
  "entry_time": "2023-10-18T10:00:00+00:00",
  "status": "active"
}
```

### Process Vehicle Exit

```bash
curl -X POST http://localhost:8000/ticket/550e8400-e29b-41d4-a716-446655440000/pay \
  -H "Content-Type: application/json" \
  -d '{"action": "exit"}'
```

Example response:
```json
{
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "license_plate": "AB-1234",
  "entry_time": "2023-10-18T10:00:00+00:00",
  "exit_time": "2023-10-18T11:30:00+00:00",
  "fee": 8.0,
  "currency": "EUR",
  "status": "paid",
  "fee_details": {
    "entry_time": "2023-10-18T10:00:00+00:00",
    "exit_time": "2023-10-18T11:30:00+00:00",
    "duration_minutes": 90.0,
    "duration_hours": 1.5,
    "fifteen_min_blocks": 6,
    "days_charged": 0,
    "remaining_hours": 1.5,
    "fee_amount": 8.0,
    "currency": "EUR"
  }
}
```

### Query Tickets

```bash
# All tickets
curl http://localhost:8000/tickets

# Filter by license plate
curl http://localhost:8000/tickets?plate=AB-1234

# Open tickets only
curl http://localhost:8000/tickets?open=true

# Combination
curl http://localhost:8000/tickets?plate=AB-1234&open=true
```

### Get Ticket by ID

```bash
curl http://localhost:8000/ticket/550e8400-e29b-41d4-a716-446655440000
```

## Deployment

### Prerequisites

- AWS CLI configured with appropriate permissions
- SSH access to an Amazon Linux 2023 EC2 instance
- Python 3.9 or higher

### Automated EC2 Deployment

1. Launch an EC2 instance with Amazon Linux 2023
2. Copy the project files to the instance:
   ```bash
   scp -r ParkingLotSystem/ ec2-user@your-ec2-instance-ip:~/
   ```

3. SSH into your EC2 instance:
   ```bash
   ssh ec2-user@your-ec2-instance-ip
   ```

4. Run the setup script:
   ```bash
   cd ParkingLotSystem/deploy
   chmod +x ec2_setup.sh
   sudo ./ec2_setup.sh
   ```

### CloudFormation Deployment (Alternative)

1. Create a CloudFormation stack using the template:
   ```bash
   aws cloudformation create-stack \
     --stack-name parking-lot-system \
     --template-body file://deploy/template.yaml \
     --capabilities CAPABILITY_IAM
   ```

2. SSH into the created EC2 instance
3. The setup script should run automatically as part of the user-data

### Manual EC2 Setup

For manual deployment, follow the instructions in `deploy/manual_ec2_deployment.sh`. This file contains step-by-step instructions for:
- Setting up DynamoDB
- Configuring the EC2 instance
- Installing dependencies
- Setting up the systemd service

## Cleanup

To clean up all resources:

1. Delete the DynamoDB table:
   ```bash
   aws dynamodb delete-table --table-name parking-tickets
   ```

2. Terminate the EC2 instance
3. Remove any associated security groups, IAM roles, etc.

If using CloudFormation:
```bash
aws cloudformation delete-stack --stack-name parking-lot-system
```
- EC2 instance (if deployed)
- IAM roles and policies
- CloudWatch log groups

## License

This project is licensed under the MIT License - see the LICENSE file for details.
