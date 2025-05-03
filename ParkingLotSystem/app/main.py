import logging
import os
import json
import sys
from typing import List, Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from db import DynamoDBTicketStore
from utils import (
    calculate_parking_fee,
    format_ticket_response, 
    generate_ticket_id,
    get_current_time
)

# Configure logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)

# Initialize FastAPI app
app = FastAPI(
    title="Parking Lot Management System",
    description="API for managing parking lot entries, exits, and fee calculations",
    version="1.0.0",
)

# Log the configuration
logger.info(f"Starting application with AWS region: {os.getenv('AWS_REGION', 'eu-central-1')}")
logger.info(f"Using DynamoDB table: {os.getenv('DYNAMODB_TABLE', 'parking-tickets')}")
logger.info(f"Using local DynamoDB: {os.getenv('DYNAMODB_LOCAL', 'False')}")

# Initialize DynamoDB store
ticket_store = DynamoDBTicketStore()

# Pydantic models
class EntryRequest(BaseModel):
    license_plate: str = Field(..., description="License plate of the vehicle")

class ExitRequest(BaseModel):
    action: str = Field(..., description="Action to perform (must be 'exit')")

class TicketResponse(BaseModel):
    ticket_id: str
    license_plate: str
    entry_time: str
    status: str
    exit_time: Optional[str] = None
    fee: Optional[float] = None
    currency: Optional[str] = None

class ErrorResponse(BaseModel):
    detail: str

@app.post(
    "/entry",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Vehicle already parked"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def create_entry(entry_request: EntryRequest, response: Response):
    """
    Create a new parking ticket for a vehicle entry
    """
    license_plate = entry_request.license_plate
    logger.info(f"Received entry request for license plate: {license_plate}")
    
    try:
        # Check if license plate is already parked
        if ticket_store.is_license_plate_parked(license_plate):
            logger.warning(f"License plate {license_plate} is already parked")
            response.status_code = status.HTTP_409_CONFLICT
            return {"detail": f"Vehicle with license plate {license_plate} is already parked"}
        
        # Create new ticket
        ticket_id = generate_ticket_id()
        entry_time = get_current_time()
        ticket = ticket_store.create_ticket(ticket_id, license_plate, entry_time)
        
        logger.info(f"Created ticket {ticket_id} for license plate {license_plate}")
        return format_ticket_response(ticket)
    
    except Exception as e:
        logger.error(f"Error creating entry: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"detail": "Internal server error"}

@app.post(
    "/ticket/{ticket_id}/pay",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Ticket not found"},
        409: {"model": ErrorResponse, "description": "Ticket already paid"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def exit_parking(ticket_id: str, exit_request: ExitRequest, response: Response):
    """
    Process vehicle exit and calculate parking fee
    """
    logger.info(f"Received exit request for ticket: {ticket_id}")
    
    if exit_request.action != "exit":
        logger.warning(f"Invalid action: {exit_request.action}")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"detail": "Invalid action. Must be 'exit'"}
    
    try:
        # Get the ticket
        ticket = ticket_store.get_ticket(ticket_id)
        
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found")
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"detail": f"Ticket {ticket_id} not found"}
        
        # Check if ticket is already paid
        if ticket.get("status") != "active":
            logger.warning(f"Ticket {ticket_id} is already paid")
            response.status_code = status.HTTP_409_CONFLICT
            return {"detail": f"Ticket {ticket_id} is already paid"}
        
        # Calculate fee
        exit_time = get_current_time()
        fee, fee_details = calculate_parking_fee(ticket["entry_time"], exit_time)
        
        # Update ticket with exit information
        updated_ticket = ticket_store.update_ticket_exit(ticket_id, exit_time, fee)
        
        # Add fee calculation details to the response
        response_data = format_ticket_response(updated_ticket)
        response_data["fee_details"] = fee_details
        
        logger.info(f"Processed exit for ticket {ticket_id}, fee: {fee} EUR")
        return response_data
    
    except Exception as e:
        logger.error(f"Error processing exit: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"detail": "Internal server error"}

@app.patch(
    "/ticket/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid action"},
        404: {"model": ErrorResponse, "description": "Ticket not found"},
        409: {"model": ErrorResponse, "description": "Ticket already paid"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_ticket(ticket_id: str, exit_request: ExitRequest, response: Response):
    """
    Alternative endpoint to process vehicle exit via PATCH
    """
    # Reuse the same logic from the POST endpoint
    return await exit_parking(ticket_id, exit_request, response)

@app.get(
    "/tickets",
    response_model=List[TicketResponse],
    status_code=status.HTTP_200_OK,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_tickets(
    response: Response,
    plate: Optional[str] = Query(None, description="Filter by license plate"),
    open: bool = Query(False, description="Filter for open tickets only")
):
    """
    Query tickets with optional filters
    """
    logger.info(f"Querying tickets with filters: plate={plate}, open={open}")
    
    try:
        tickets = ticket_store.query_tickets(license_plate=plate, open_only=open)
        return [format_ticket_response(ticket) for ticket in tickets]
    
    except Exception as e:
        logger.error(f"Error querying tickets: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"detail": "Internal server error"}

@app.get(
    "/ticket/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Ticket not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_ticket(ticket_id: str, response: Response):
    """
    Get ticket details by ID
    """
    logger.info(f"Retrieving ticket: {ticket_id}")
    
    try:
        ticket = ticket_store.get_ticket(ticket_id)
        
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found")
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"detail": f"Ticket {ticket_id} not found"}
        
        return format_ticket_response(ticket)
    
    except Exception as e:
        logger.error(f"Error retrieving ticket: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"detail": "Internal server error"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

# Note: Serverless/Lambda deployment has been removed from this project

if __name__ == "__main__":
    # Run the app directly when executed as a script
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
