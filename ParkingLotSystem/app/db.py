import os
import boto3
import logging
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class DynamoDBTicketStore:
    """
    Handles interactions with DynamoDB for parking ticket management
    """
    def __init__(self):
        # Use environment variables for AWS configuration
        self.region = os.getenv('AWS_REGION', 'eu-central-1')
        self.table_name = os.getenv('DYNAMODB_TABLE', 'parking-tickets')
        
        # Initialize DynamoDB client
        if os.getenv('AWS_SAM_LOCAL') or os.getenv('DYNAMODB_LOCAL'):
            # Use local DynamoDB endpoint for local development
            endpoint_url = os.getenv('DYNAMODB_ENDPOINT', 'http://localhost:8000')
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region, endpoint_url=endpoint_url)
        else:
            # Use AWS credentials from environment variables in production
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        
        self.table = self.dynamodb.Table(self.table_name)
        logger.info(f"Initialized DynamoDB connection to table: {self.table_name}")

    def create_ticket(self, ticket_id: str, license_plate: str, entry_time: str) -> Dict[str, Any]:
        """
        Create a new parking ticket
        """
        item = {
            'ticket_id': ticket_id,
            'license_plate': license_plate,
            'entry_time': entry_time,
            'status': 'active'
        }

        try:
            self.table.put_item(Item=item)
            logger.info(f"Created ticket: {ticket_id} for license plate: {license_plate}")
            return item
        except ClientError as e:
            logger.error(f"Failed to create ticket: {e}")
            raise

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a ticket by ID
        """
        try:
            response = self.table.get_item(Key={'ticket_id': ticket_id})
            ticket = response.get('Item')
            if ticket:
                logger.info(f"Retrieved ticket: {ticket_id}")
            else:
                logger.info(f"Ticket not found: {ticket_id}")
            return ticket
        except ClientError as e:
            logger.error(f"Error retrieving ticket {ticket_id}: {e}")
            raise

    def update_ticket_exit(self, ticket_id: str, exit_time: str, fee: float) -> Optional[Dict[str, Any]]:
        """
        Update a ticket with exit information and fee
        """
        try:
            response = self.table.update_item(
                Key={'ticket_id': ticket_id},
                UpdateExpression='SET exit_time = :exit_time, fee = :fee, status = :status',
                ExpressionAttributeValues={
                    ':exit_time': exit_time,
                    ':fee': fee,
                    ':status': 'paid'
                },
                ReturnValues='ALL_NEW'
            )
            updated_ticket = response.get('Attributes')
            logger.info(f"Updated ticket {ticket_id} with exit time and fee")
            return updated_ticket
        except ClientError as e:
            logger.error(f"Error updating ticket {ticket_id}: {e}")
            raise

    def query_tickets(self, license_plate: Optional[str] = None, open_only: bool = False) -> List[Dict[str, Any]]:
        """
        Query tickets with optional filters
        """
        try:
            if license_plate:
                # Query by license plate using secondary index
                if open_only:
                    response = self.table.query(
                        IndexName='license_plate-index',
                        KeyConditionExpression='license_plate = :plate',
                        FilterExpression='status = :status',
                        ExpressionAttributeValues={
                            ':plate': license_plate,
                            ':status': 'active'
                        }
                    )
                else:
                    response = self.table.query(
                        IndexName='license_plate-index',
                        KeyConditionExpression='license_plate = :plate',
                        ExpressionAttributeValues={
                            ':plate': license_plate
                        }
                    )
                logger.info(f"Queried tickets for license plate: {license_plate}")
            elif open_only:
                # Scan for open tickets only (not efficient for large datasets)
                response = self.table.scan(
                    FilterExpression='status = :status',
                    ExpressionAttributeValues={
                        ':status': 'active'
                    }
                )
                logger.info("Queried all open tickets")
            else:
                # Get all tickets (not recommended for large datasets)
                response = self.table.scan()
                logger.info("Queried all tickets")
            
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error querying tickets: {e}")
            raise

    def is_license_plate_parked(self, license_plate: str) -> bool:
        """
        Check if a license plate is already parked (has an active ticket)
        """
        try:
            response = self.table.query(
                IndexName='license_plate-index',
                KeyConditionExpression='license_plate = :plate',
                FilterExpression='status = :status',
                ExpressionAttributeValues={
                    ':plate': license_plate,
                    ':status': 'active'
                }
            )
            is_parked = len(response.get('Items', [])) > 0
            logger.info(f"Checked if license plate {license_plate} is parked: {is_parked}")
            return is_parked
        except ClientError as e:
            logger.error(f"Error checking if license plate {license_plate} is parked: {e}")
            raise
