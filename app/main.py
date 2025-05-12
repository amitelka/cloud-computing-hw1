from __future__ import annotations

import logging
import os
import json
import sys
import uuid

import uvicorn
from fastapi import FastAPI, Query, status
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError

from db import DynamoDBTicketStore
from utils import (
    calculate_parking_fee,
    generate_ticket_id,
    get_current_time,
    validate_license_plate_format
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

# Initialize DynamoDB store
ticket_store: DynamoDBTicketStore = DynamoDBTicketStore()

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

@app.post("/entry")
async def entry_endpoint(
    plate: str = Query(..., description="License plate for entry"),
    parkingLot: str = Query(..., description="Parking lot identifier for entry")
):
    """
    Entry endpoint following the exact format from the assignment:
    POST /entry?plate=123-123-123&parkingLot=382
    
    Returns ticket ID
    """
    logger.info(f"Entry request for plate: {plate} at parking lot: {parkingLot}")
    if not validate_license_plate_format(plate):
        logger.warning(f"Invalid license plate format: {plate}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": f"Invalid license plate format: {plate}"}
        )

    try:
        # Check if license plate is already parked
        if ticket_store.is_license_plate_parked(plate):
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": f"Vehicle with license plate {plate} is already parked"}
            )
        
        # Create new ticket
        ticket_id = generate_ticket_id()
        entry_time = get_current_time()
        
        # Create the ticket
        ticket_store.create_ticket(ticket_id, plate, entry_time)

        try:
            ticket_store.table.update_item(
                Key={'ticket_id': ticket_id},
                UpdateExpression='SET parking_lot = :pl',
                ExpressionAttributeValues={':pl': parkingLot}
            )
        except Exception as e:
            logger.warning(f"Could not add parking lot info to ticket: {e}")

        # Simply return the ticket ID as specified in the assignment
        return {"ticketId": ticket_id}
        
    except Exception as e:
        logger.error(f"Error creating entry: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

@app.post("/exit")
async def exit_endpoint(
    ticketId: str = Query(..., description="Ticket ID for exit")
):
    """
    Exit endpoint following the exact format from the assignment:
    POST /exit?ticketId=1234
    
    Returns the license plate, total parked time, parking lot ID and the charge
    """
    logger.info(f"Exit request for ticket: {ticketId}")
    try:
        ticket = ticket_store.get_ticket(ticketId)
        
        if not ticket:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND, 
                content={"detail": f"Ticket {ticketId} not found"}
            )

        if ticket.get("payment_status") == "pending_payment":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT, 
                content={"detail": f"Exit request for ticket {ticketId} was already processed"}
            )

        if ticket.get("payment_status") == "paid":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT, 
                content={"detail": f"Ticket {ticketId} is already paid"}
            )
            
        exit_time = get_current_time()
        fee, fee_details = calculate_parking_fee(ticket["entry_time"], exit_time)

        # Update ticket with exit information
        updated_ticket = ticket_store.update_ticket_exit(ticketId, exit_time, fee)

        logger.info(f"Processed exit for ticket {ticketId}, fee: ${fee} USD")
        
        # Return format matching the assignment requirement
        return {
            "licensePlate": updated_ticket["license_plate"],
            "totalParkedTime": fee_details["duration_minutes"],
            "parkingLot": ticket.get("parking_lot", "N/A"),
            "charge": fee
        }
        
    except Exception as e:
        logger.error(f"Error processing exit: {str(e)}")

        if isinstance(e, ClientError) and e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": f"Exit request for ticket {ticketId} was already processed"},
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

@app.post("/pay")
async def pay_endpoint(
    ticketId: str = Query(..., description="Ticket ID to settle"),
):
    """
    Stub payment endpoint.
    Accepts *any* `mockPaymentToken`, charges the amount that `/exit`
    recorded, and moves the ticket to *paid*.
    """
    ticket = ticket_store.get_ticket(ticketId)
    if not ticket:
        logger.warning(f"Ticket {ticketId} not found")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Ticket {ticketId} not found"}
        )

    if ticket["payment_status"] == "paid":
        logger.warning(f"Ticket {ticketId} already paid")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": f"Ticket {ticketId} is already settled"}
        )
    if ticket["payment_status"] != "pending_payment":
        logger.warning(f"Ticket {ticketId} is in unexpected state: {ticket['payment_status']}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": f"Ticket is in unexpected state {ticket['payment_status']}"}
        )

    fake_tx_id = f"tx-{uuid.uuid4()}"      # pretend the PSP returned this

    updated = ticket_store.mark_ticket_paid(
        ticket_id=ticketId,
        tx_id=fake_tx_id
    )
    logger.info(f"Processed payment for ticket {ticketId}, transaction ID: {fake_tx_id}, {updated}")

    return {
        "ticketId": ticketId,
        "licensePlate": updated["license_plate"],
        "charged": ticket["fee"],
        "currency": "USD",
        "transactionId": fake_tx_id,
        "payment_status": "paid"
    }


if __name__ == "__main__":
    # Run the app directly when executed as a script
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
