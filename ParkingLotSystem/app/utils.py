import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple


def generate_ticket_id() -> str:
    """Generate a unique ticket ID"""
    return str(uuid.uuid4())


def get_current_time() -> str:
    """Get current UTC time in ISO 8601 format"""
    return datetime.now(timezone.utc).isoformat()


def calculate_parking_fee(entry_time_str: str, exit_time_str: str) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate the parking fee based on entry and exit times
    
    Rules:
    1. First 15 min block is always charged
    2. Billing unit = 15 min
    3. Rate = 2 € per 15 min (8 €/h)
    4. Partial blocks are rounded up
    5. Daily cap: 40 € per 24h
    
    Returns:
        Tuple containing the fee amount and a dictionary with calculation details
    """
    # Parse ISO 8601 timestamps
    entry_time = datetime.fromisoformat(entry_time_str)
    exit_time = datetime.fromisoformat(exit_time_str)
    
    # Calculate duration in minutes
    duration_seconds = (exit_time - entry_time).total_seconds()
    duration_minutes = duration_seconds / 60
    duration_hours = duration_minutes / 60
    
    # Convert to 15-minute blocks (always round up)
    blocks = math.ceil(duration_minutes / 15)
    
    # Calculate base fee (2€ per block)
    base_fee = blocks * 2
    
    # Apply daily cap (40€ per 24h)
    days = math.floor(duration_hours / 24)
    remaining_hours = duration_hours % 24
    remaining_blocks = math.ceil(remaining_hours * 4)  # 4 blocks per hour
    
    fee = (days * 40) + min(40, remaining_blocks * 2)
    
    # Prepare calculation details
    details = {
        "entry_time": entry_time_str,
        "exit_time": exit_time_str,
        "duration_minutes": round(duration_minutes, 2),
        "duration_hours": round(duration_hours, 2),
        "fifteen_min_blocks": blocks,
        "days_charged": days,
        "remaining_hours": round(remaining_hours, 2),
        "fee_amount": fee,
        "currency": "EUR"
    }
    
    return fee, details


def format_ticket_response(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """Format a ticket for API response"""
    response = {
        "ticket_id": ticket["ticket_id"],
        "license_plate": ticket["license_plate"],
        "entry_time": ticket["entry_time"],
        "status": ticket["status"]
    }
    
    # Include exit details if available
    if "exit_time" in ticket:
        response["exit_time"] = ticket["exit_time"]
    if "fee" in ticket:
        response["fee"] = ticket["fee"]
        response["currency"] = "EUR"
    
    return response
