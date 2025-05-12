import os
import logging
from typing import Dict, Optional, Any
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table

logger = logging.getLogger(__name__)


class DynamoDBTicketStore:
    """
    Handles interactions with DynamoDB for parking ticket management
    """

    def __init__(self):
        self.region = os.getenv("AWS_REGION", "eu-central-1")
        self.table_name = os.getenv("DYNAMODB_TABLE", "parking-tickets")

        self.dynamodb: DynamoDBServiceResource = boto3.resource(
            "dynamodb", region_name=self.region
        )
        self.table: Table = self.dynamodb.Table(self.table_name)
        logger.info(f"Initialized DynamoDB connection to table: {self.table_name}")

    def create_ticket(
        self, ticket_id: str, license_plate: str, entry_time: str
    ) -> Dict[str, Any]:
        item = {
            "ticket_id": ticket_id,
            "license_plate": license_plate,
            "entry_time": entry_time,
            "payment_status": "active",
        }
        try:
            self.table.put_item(Item=item)
            logger.info(f"Created ticket {ticket_id} for license plate {license_plate}")
            return item
        except ClientError as e:
            logger.error(f"Failed to create ticket: {e}")
            raise

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self.table.get_item(Key={"ticket_id": ticket_id})
            return resp.get("Item")
        except ClientError as e:
            logger.error(f"Error fetching ticket {ticket_id}: {e}")
            raise

    def update_ticket_exit(
        self, ticket_id: str, exit_time: str, fee: Decimal
    ) -> Optional[Dict[str, Any]]:
        try:
            resp = self.table.update_item(
                Key={"ticket_id": ticket_id},
                ConditionExpression=Attr("payment_status").eq("active"),
                UpdateExpression="SET exit_time = :exit_time, fee = :fee, payment_status = :payment_status, currency = :currency",
                ExpressionAttributeValues={
                    ":exit_time": exit_time,
                    ":fee": fee,
                    ":payment_status": "pending_payment",
                    ":currency": "USD",
                },
                ReturnValues="ALL_NEW",
            )
            logger.info(f"Updated ticket {ticket_id} with exit time and fee {fee} USD")
            return resp.get("Attributes")
        except ClientError as e:
            logger.error(f"Error updating ticket {ticket_id}: {e}")
            raise

    def mark_ticket_paid(self, ticket_id: str, tx_id: str) -> Dict[str, Any]:
        try:
            resp = self.table.update_item(
                Key={"ticket_id": ticket_id},
                UpdateExpression="SET payment_status = :paid, tx_id = :tx",
                ExpressionAttributeValues={
                    ":paid": "paid",
                    ":tx": tx_id,
                },
                ReturnValues="ALL_NEW",
            )
            return resp["Attributes"]
        except ClientError as e:
            logger.error(f"Could not mark ticket {ticket_id} paid: {e}")
            raise

    def is_license_plate_parked(self, license_plate: str) -> bool:
        """
        Returns True if license_plate currently has an *active* ticket.
        Uses the GSI `license_plate-index`.
        """
        try:
            resp = self.table.query(
                IndexName="license_plate-index",
                KeyConditionExpression=Key("license_plate").eq(license_plate),
                FilterExpression=Attr("payment_status").eq("active"),
            )
            parked = bool(resp.get("Items"))
            logger.info(f"License plate {license_plate} parked: {parked}")
            return parked
        except ClientError as e:
            logger.error(f"Error checking plate {license_plate}: {e}")
            raise
