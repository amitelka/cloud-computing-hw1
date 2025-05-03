import os
import pytest
import boto3
import json
from unittest import mock
from moto import mock_dynamodb

from app.db import DynamoDBTicketStore


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-central-1"


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table for testing"""
    with mock_dynamodb():
        # Set up the DynamoDB table
        region = "eu-central-1"
        table_name = "parking-tickets-test"
        
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "ticket_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "ticket_id", "AttributeType": "S"},
                {"AttributeName": "license_plate", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "license_plate-index",
                    "KeySchema": [{"AttributeName": "license_plate", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                }
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
        )
        
        # Set environment variables for the test
        os.environ["DYNAMODB_TABLE"] = table_name
        os.environ["AWS_REGION"] = region
        
        yield table


@pytest.fixture
def ticket_store(dynamodb_table):
    """Create a ticket store instance with the mock table"""
    return DynamoDBTicketStore()


def test_create_ticket(ticket_store):
    """Test creating a ticket in DynamoDB"""
    ticket_id = "test-ticket-123"
    license_plate = "AB-1234"
    entry_time = "2023-10-18T10:00:00+00:00"
    
    # Create a ticket
    result = ticket_store.create_ticket(ticket_id, license_plate, entry_time)
    
    # Verify the result
    assert result["ticket_id"] == ticket_id
    assert result["license_plate"] == license_plate
    assert result["entry_time"] == entry_time
    assert result["status"] == "active"
    
    # Verify the ticket was stored
    stored_ticket = ticket_store.get_ticket(ticket_id)
    assert stored_ticket["ticket_id"] == ticket_id
    assert stored_ticket["license_plate"] == license_plate
    assert stored_ticket["entry_time"] == entry_time
    assert stored_ticket["status"] == "active"


def test_get_ticket_not_found(ticket_store):
    """Test getting a non-existent ticket"""
    ticket_id = "non-existent-ticket"
    
    # Try to get a ticket that doesn't exist
    stored_ticket = ticket_store.get_ticket(ticket_id)
    
    # Verify the result
    assert stored_ticket is None


def test_update_ticket_exit(ticket_store):
    """Test updating a ticket with exit information"""
    # Create a ticket first
    ticket_id = "test-ticket-123"
    license_plate = "AB-1234"
    entry_time = "2023-10-18T10:00:00+00:00"
    ticket_store.create_ticket(ticket_id, license_plate, entry_time)
    
    # Update the ticket with exit information
    exit_time = "2023-10-18T11:30:00+00:00"
    fee = 12.0
    updated_ticket = ticket_store.update_ticket_exit(ticket_id, exit_time, fee)
    
    # Verify the result
    assert updated_ticket["ticket_id"] == ticket_id
    assert updated_ticket["license_plate"] == license_plate
    assert updated_ticket["entry_time"] == entry_time
    assert updated_ticket["exit_time"] == exit_time
    assert updated_ticket["fee"] == fee
    assert updated_ticket["status"] == "paid"
    
    # Verify the ticket was updated in storage
    stored_ticket = ticket_store.get_ticket(ticket_id)
    assert stored_ticket["exit_time"] == exit_time
    assert stored_ticket["fee"] == fee
    assert stored_ticket["status"] == "paid"


def test_query_tickets(ticket_store):
    """Test querying tickets"""
    # Create some test tickets
    ticket_store.create_ticket("ticket-1", "AB-1234", "2023-10-18T10:00:00+00:00")
    ticket_store.create_ticket("ticket-2", "CD-5678", "2023-10-18T11:00:00+00:00")
    ticket_store.create_ticket("ticket-3", "AB-1234", "2023-10-19T10:00:00+00:00")
    
    # Mark one as paid
    ticket_store.update_ticket_exit("ticket-1", "2023-10-18T12:00:00+00:00", 8.0)
    
    # Test querying all tickets
    all_tickets = ticket_store.query_tickets()
    assert len(all_tickets) == 3
    
    # Test querying by license plate
    plate_tickets = ticket_store.query_tickets(license_plate="AB-1234")
    assert len(plate_tickets) == 2
    assert all(ticket["license_plate"] == "AB-1234" for ticket in plate_tickets)
    
    # Test querying open tickets
    open_tickets = ticket_store.query_tickets(open_only=True)
    assert len(open_tickets) == 2
    assert all(ticket["status"] == "active" for ticket in open_tickets)
    
    # Test querying open tickets by license plate
    open_plate_tickets = ticket_store.query_tickets(license_plate="AB-1234", open_only=True)
    assert len(open_plate_tickets) == 1
    assert open_plate_tickets[0]["license_plate"] == "AB-1234"
    assert open_plate_tickets[0]["status"] == "active"


def test_is_license_plate_parked(ticket_store):
    """Test checking if a license plate is already parked"""
    # Create some test tickets
    ticket_store.create_ticket("ticket-1", "AB-1234", "2023-10-18T10:00:00+00:00")
    ticket_store.create_ticket("ticket-2", "CD-5678", "2023-10-18T11:00:00+00:00")
    
    # Mark one as paid
    ticket_store.update_ticket_exit("ticket-1", "2023-10-18T12:00:00+00:00", 8.0)
    
    # Check for active tickets
    assert ticket_store.is_license_plate_parked("CD-5678") is True
    assert ticket_store.is_license_plate_parked("AB-1234") is False  # Paid, so not active
    assert ticket_store.is_license_plate_parked("EF-9012") is False  # Doesn't exist
