import pytest
from unittest import mock
from datetime import datetime, timezone, timedelta

from app.utils import (
    generate_ticket_id,
    get_current_time,
    calculate_parking_fee,
    format_ticket_response
)


def test_generate_ticket_id():
    """Test ticket ID generation"""
    ticket_id_1 = generate_ticket_id()
    ticket_id_2 = generate_ticket_id()
    
    # IDs should be unique
    assert ticket_id_1 != ticket_id_2
    
    # IDs should be strings
    assert isinstance(ticket_id_1, str)
    assert isinstance(ticket_id_2, str)


def test_get_current_time():
    """Test current time retrieval"""
    time_str = get_current_time()
    
    # Should be in ISO 8601 format
    try:
        dt = datetime.fromisoformat(time_str)
    except ValueError:
        pytest.fail(f"Invalid ISO 8601 time format: {time_str}")
    
    # Should be in UTC timezone
    assert dt.tzinfo is not None
    
    # Should be close to now
    now = datetime.now(timezone.utc)
    diff = now - dt
    assert diff.total_seconds() < 5  # Within 5 seconds


def test_calculate_parking_fee_short_stay():
    """Test fee calculation for a short stay (single block)"""
    entry_time = "2023-10-18T10:00:00+00:00"
    exit_time = "2023-10-18T10:07:00+00:00"
    
    fee, details = calculate_parking_fee(entry_time, exit_time)
    
    # First 15 min block is always charged
    assert fee == 2.0
    assert details["fifteen_min_blocks"] == 1
    assert details["fee_amount"] == 2.0
    assert details["currency"] == "EUR"


def test_calculate_parking_fee_multiple_blocks():
    """Test fee calculation for multiple blocks"""
    entry_time = "2023-10-18T10:00:00+00:00"
    exit_time = "2023-10-18T11:05:00+00:00"
    
    fee, details = calculate_parking_fee(entry_time, exit_time)
    
    # 1h 5min = 5 blocks = 10€
    assert fee == 10.0
    assert details["fifteen_min_blocks"] == 5
    assert details["fee_amount"] == 10.0
    assert details["days_charged"] == 0


def test_calculate_parking_fee_with_daily_cap():
    """Test fee calculation with daily cap"""
    entry_time = "2023-10-18T10:00:00+00:00"
    exit_time = "2023-10-19T10:00:00+00:00"
    
    fee, details = calculate_parking_fee(entry_time, exit_time)
    
    # 24h = daily cap of 40€
    assert fee == 40.0
    assert details["days_charged"] == 1
    assert details["remaining_hours"] == 0
    assert details["fee_amount"] == 40.0


def test_calculate_parking_fee_beyond_daily_cap():
    """Test fee calculation beyond daily cap"""
    entry_time = "2023-10-18T10:00:00+00:00"
    exit_time = "2023-10-19T22:00:00+00:00"
    
    fee, details = calculate_parking_fee(entry_time, exit_time)
    
    # 36h = 1 day (40€) + 12h (8 blocks = 16€, but capped at 8€ per remaining hours)
    assert fee == 48.0
    assert details["days_charged"] == 1
    assert details["remaining_hours"] == 12.0
    assert details["fee_amount"] == 48.0


def test_format_ticket_response():
    """Test ticket formatting for API response"""
    # Active ticket
    active_ticket = {
        "ticket_id": "test-ticket-123",
        "license_plate": "AB-1234",
        "entry_time": "2023-10-18T10:00:00+00:00",
        "status": "active",
        "extra_field": "should_not_be_included"
    }
    
    formatted_active = format_ticket_response(active_ticket)
    
    assert formatted_active["ticket_id"] == "test-ticket-123"
    assert formatted_active["license_plate"] == "AB-1234"
    assert formatted_active["entry_time"] == "2023-10-18T10:00:00+00:00"
    assert formatted_active["status"] == "active"
    assert "exit_time" not in formatted_active
    assert "fee" not in formatted_active
    assert "extra_field" not in formatted_active
    
    # Paid ticket
    paid_ticket = {
        "ticket_id": "test-ticket-456",
        "license_plate": "CD-5678",
        "entry_time": "2023-10-18T10:00:00+00:00",
        "exit_time": "2023-10-18T12:00:00+00:00",
        "fee": 8.0,
        "status": "paid",
        "extra_field": "should_not_be_included"
    }
    
    formatted_paid = format_ticket_response(paid_ticket)
    
    assert formatted_paid["ticket_id"] == "test-ticket-456"
    assert formatted_paid["license_plate"] == "CD-5678"
    assert formatted_paid["entry_time"] == "2023-10-18T10:00:00+00:00"
    assert formatted_paid["exit_time"] == "2023-10-18T12:00:00+00:00"
    assert formatted_paid["fee"] == 8.0
    assert formatted_paid["currency"] == "EUR"
    assert formatted_paid["status"] == "paid"
    assert "extra_field" not in formatted_paid
