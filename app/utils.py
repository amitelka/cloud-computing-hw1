import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
import re
from decimal import Decimal


PLATE_PATTERNS = [
    r'^\d{3}-\d{2}-\d{3}$',
    r'^\d{3}-\d{3}-\d{3}$',
    r'^\d{2}-\d{3}-\d{2}$'
]

def generate_ticket_id() -> str:
    """Generate a unique ticket ID"""
    return str(uuid.uuid4())


def get_current_time() -> str:
    """Get current UTC time in ISO 8601 format"""
    return datetime.now(timezone.utc).isoformat()

def validate_license_plate_format(plate: str) -> bool:
    return any(re.match(p, plate) for p in PLATE_PATTERNS)

def calculate_parking_fee(entry_time_str: str, exit_time_str: str) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate the parking fee based on entry and exit times
    
    Rules:
    1. First 15 min block is always charged
    2. Billing unit = 15 min
    3. Rate = $2.50 per 15 min ($10/h)
    4. Partial blocks are rounded up
    
    Returns:
        Tuple containing the fee amount and a dictionary with calculation details
    """
    entry_time = datetime.fromisoformat(entry_time_str)
    exit_time = datetime.fromisoformat(exit_time_str)
    
    # Calculate duration in minutes
    duration_seconds = (exit_time - entry_time).total_seconds()
    duration_minutes = duration_seconds / 60
    duration_hours = duration_minutes / 60
    blocks = max(1, math.ceil(duration_minutes / 15))
    
    base_fee = blocks * 2.5
    fee = base_fee
    fee = Decimal(str(fee))
    
    # Prepare calculation details
    details = {
        "entry_time": entry_time_str,
        "exit_time": exit_time_str,
        "duration_minutes": round(duration_minutes, 2),
        "duration_hours": round(duration_hours, 2),
        "fifteen_min_blocks": blocks,
        "fee_amount": fee,
        "currency": "USD"
    }
    
    return fee, details


def format_ticket_response(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """Format a ticket for API response"""
    response = {
        "ticket_id": ticket["ticket_id"],
        "license_plate": ticket["license_plate"],
        "entry_time": ticket["entry_time"],
        "payment_status": ticket["payment_status"]
    }

    # Include exit details if available
    if "exit_time" in ticket:
        response["exit_time"] = ticket["exit_time"]

    if "fee" in ticket:
        response["fee"] = ticket["fee"]
        response["currency"] = "USD"  # Changed to USD per assignment spec

    # Include parking lot if available
    if "parking_lot" in ticket:
        response["parking_lot"] = ticket["parking_lot"]
    
    return response
