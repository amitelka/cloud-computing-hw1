import os
import uuid
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest import mock
from fastapi.testclient import TestClient

# Set environment variables for testing
os.environ["DYNAMODB_LOCAL"] = "True"
os.environ["DYNAMODB_ENDPOINT"] = "http://localhost:8000"
os.environ["DYNAMODB_TABLE"] = "parking-tickets-test"
os.environ["AWS_REGION"] = "eu-central-1"

# Import main app and db modules after environment variables are set
from app.main import app
from app.db import DynamoDBTicketStore
from app.utils import calculate_parking_fee, generate_ticket_id, get_current_time

# Create a test client
client = TestClient(app)


@pytest.fixture
def mock_db():
    """Mock DynamoDB ticket store"""
    with mock.patch("app.main.ticket_store") as mock_store:
        yield mock_store


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_entry_success(mock_db):
    """Test successful entry creation"""
    mock_ticket_id = "test-ticket-123"
    mock_entry_time = "2023-10-18T10:00:00+00:00"
    
    # Mock the UUID and timestamp generation
    with mock.patch("app.utils.generate_ticket_id", return_value=mock_ticket_id):
        with mock.patch("app.utils.get_current_time", return_value=mock_entry_time):
            # Mock the is_license_plate_parked method to return False
            mock_db.is_license_plate_parked.return_value = False
            
            # Mock the create_ticket method
            mock_db.create_ticket.return_value = {
                "ticket_id": mock_ticket_id,
                "license_plate": "AB-1234",
                "entry_time": mock_entry_time,
                "status": "active"
            }
            
            # Make the request
            response = client.post("/entry", json={"license_plate": "AB-1234"})
            
            # Verify the response
            assert response.status_code == 201
            assert response.json() == {
                "ticket_id": mock_ticket_id,
                "license_plate": "AB-1234",
                "entry_time": mock_entry_time,
                "status": "active"
            }
            
            # Verify the mock was called correctly
            mock_db.is_license_plate_parked.assert_called_once_with("AB-1234")
            mock_db.create_ticket.assert_called_once_with(mock_ticket_id, "AB-1234", mock_entry_time)


def test_create_entry_duplicate(mock_db):
    """Test entry creation with already parked vehicle"""
    # Mock the is_license_plate_parked method to return True
    mock_db.is_license_plate_parked.return_value = True
    
    # Make the request
    response = client.post("/entry", json={"license_plate": "AB-1234"})
    
    # Verify the response
    assert response.status_code == 409
    assert "already parked" in response.json()["detail"]
    
    # Verify the mock was called correctly
    mock_db.is_license_plate_parked.assert_called_once_with("AB-1234")
    mock_db.create_ticket.assert_not_called()


def test_exit_parking_success(mock_db):
    """Test successful exit and fee calculation"""
    ticket_id = "test-ticket-123"
    entry_time = "2023-10-18T10:00:00+00:00"
    exit_time = "2023-10-18T11:30:00+00:00"
    
    # Mock the get_ticket method
    mock_db.get_ticket.return_value = {
        "ticket_id": ticket_id,
        "license_plate": "AB-1234",
        "entry_time": entry_time,
        "status": "active"
    }
    
    # Mock the timestamp generation
    with mock.patch("app.utils.get_current_time", return_value=exit_time):
        # Mock the update_ticket_exit method
        mock_db.update_ticket_exit.return_value = {
            "ticket_id": ticket_id,
            "license_plate": "AB-1234",
            "entry_time": entry_time,
            "exit_time": exit_time,
            "fee": 12.0,
            "status": "paid"
        }
        
        # Make the request
        response = client.post(f"/ticket/{ticket_id}/pay", json={"action": "exit"})
        
        # Verify the response
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["ticket_id"] == ticket_id
        assert json_response["license_plate"] == "AB-1234"
        assert json_response["entry_time"] == entry_time
        assert json_response["exit_time"] == exit_time
        assert json_response["fee"] == 12.0
        assert json_response["status"] == "paid"
        
        # Verify the mocks were called correctly
        mock_db.get_ticket.assert_called_once_with(ticket_id)
        mock_db.update_ticket_exit.assert_called_once()


def test_exit_parking_not_found(mock_db):
    """Test exit with non-existent ticket"""
    ticket_id = "non-existent-ticket"
    
    # Mock the get_ticket method to return None
    mock_db.get_ticket.return_value = None
    
    # Make the request
    response = client.post(f"/ticket/{ticket_id}/pay", json={"action": "exit"})
    
    # Verify the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    
    # Verify the mock was called correctly
    mock_db.get_ticket.assert_called_once_with(ticket_id)
    mock_db.update_ticket_exit.assert_not_called()


def test_exit_parking_already_paid(mock_db):
    """Test exit with already paid ticket"""
    ticket_id = "test-ticket-123"
    
    # Mock the get_ticket method to return a paid ticket
    mock_db.get_ticket.return_value = {
        "ticket_id": ticket_id,
        "license_plate": "AB-1234",
        "entry_time": "2023-10-18T10:00:00+00:00",
        "exit_time": "2023-10-18T11:30:00+00:00",
        "fee": 12.0,
        "status": "paid"
    }
    
    # Make the request
    response = client.post(f"/ticket/{ticket_id}/pay", json={"action": "exit"})
    
    # Verify the response
    assert response.status_code == 409
    assert "already paid" in response.json()["detail"]
    
    # Verify the mock was called correctly
    mock_db.get_ticket.assert_called_once_with(ticket_id)
    mock_db.update_ticket_exit.assert_not_called()


def test_get_tickets(mock_db):
    """Test querying tickets"""
    # Mock the query_tickets method
    mock_db.query_tickets.return_value = [
        {
            "ticket_id": "test-ticket-1",
            "license_plate": "AB-1234",
            "entry_time": "2023-10-18T10:00:00+00:00",
            "status": "active"
        },
        {
            "ticket_id": "test-ticket-2",
            "license_plate": "CD-5678",
            "entry_time": "2023-10-18T11:00:00+00:00",
            "status": "active"
        }
    ]
    
    # Make the request
    response = client.get("/tickets")
    
    # Verify the response
    assert response.status_code == 200
    assert len(response.json()) == 2
    
    # Verify the mock was called correctly
    mock_db.query_tickets.assert_called_once_with(license_plate=None, open_only=False)


def test_get_tickets_with_filters(mock_db):
    """Test querying tickets with filters"""
    # Mock the query_tickets method
    mock_db.query_tickets.return_value = [
        {
            "ticket_id": "test-ticket-1",
            "license_plate": "AB-1234",
            "entry_time": "2023-10-18T10:00:00+00:00",
            "status": "active"
        }
    ]
    
    # Make the request
    response = client.get("/tickets?plate=AB-1234&open=true")
    
    # Verify the response
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["license_plate"] == "AB-1234"
    
    # Verify the mock was called correctly
    mock_db.query_tickets.assert_called_once_with(license_plate="AB-1234", open_only=True)


def test_get_ticket_by_id(mock_db):
    """Test getting a ticket by ID"""
    ticket_id = "test-ticket-123"
    
    # Mock the get_ticket method
    mock_db.get_ticket.return_value = {
        "ticket_id": ticket_id,
        "license_plate": "AB-1234",
        "entry_time": "2023-10-18T10:00:00+00:00",
        "status": "active"
    }
    
    # Make the request
    response = client.get(f"/ticket/{ticket_id}")
    
    # Verify the response
    assert response.status_code == 200
    assert response.json()["ticket_id"] == ticket_id
    
    # Verify the mock was called correctly
    mock_db.get_ticket.assert_called_once_with(ticket_id)


def test_get_ticket_not_found(mock_db):
    """Test getting a non-existent ticket"""
    ticket_id = "non-existent-ticket"
    
    # Mock the get_ticket method to return None
    mock_db.get_ticket.return_value = None
    
    # Make the request
    response = client.get(f"/ticket/{ticket_id}")
    
    # Verify the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    
    # Verify the mock was called correctly
    mock_db.get_ticket.assert_called_once_with(ticket_id)


def test_calculate_parking_fee():
    """Test fee calculation logic"""
    test_cases = [
        # Case 1: 7 minutes (1 block) = 2€
        {
            "entry_time": "2023-10-18T10:00:00+00:00",
            "exit_time": "2023-10-18T10:07:00+00:00",
            "expected_fee": 2.0,
            "expected_blocks": 1
        },
        # Case 2: 1 hour and 5 minutes (5 blocks) = 10€
        {
            "entry_time": "2023-10-18T10:00:00+00:00",
            "exit_time": "2023-10-18T11:05:00+00:00",
            "expected_fee": 10.0,
            "expected_blocks": 5
        },
        # Case 3: 36 hours (144 blocks, but daily cap applies)
        # 40€ for first 24h + 8€ for extra 12h = 48€
        {
            "entry_time": "2023-10-18T10:00:00+00:00",
            "exit_time": "2023-10-19T22:00:00+00:00",
            "expected_fee": 48.0,
            "expected_days": 1
        }
    ]
    
    for case in test_cases:
        fee, details = calculate_parking_fee(case["entry_time"], case["exit_time"])
        assert fee == case["expected_fee"]
        
        if "expected_blocks" in case:
            assert details["fifteen_min_blocks"] == case["expected_blocks"]
        
        if "expected_days" in case:
            assert details["days_charged"] == case["expected_days"]
