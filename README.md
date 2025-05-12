# Parking Lot Management System

FastAPI service that issues parking-entry tickets, calculates exit fees, and stores everything in DynamoDB.  
Ships as a Docker image and a one-click AWS CloudFormation stack.

## Features

* **/entry** – opens a ticket, prevents duplicate active plates
* **/exit**  – charges prorated fee (first 15-min block always charged)
* **/pay**   – optional endpoint that marks the ticket as paid
* **Infra-as-code** – single CloudFormation stack (EC2 + DynamoDB)

## AWS deployment

### Prerequisites

* **AWS CLI** with a configured profile
* **Docker** (to build/push the image)
* An existing EC2 **Key Pair** (used for SSH)

### Deploy stack

```bash
export KEY_PAIR_NAME=<your-keypair-name>
./deploy.sh  # region, stack_name, stage, instance_type, docker_image can be tweaked at the top of the deployment script
```

---

## API reference

| Endpoint | Method | Query/body params     | Success (2xx)                                                                                                                      | Error                                                             |
| -------- | ------ | --------------------- | -----------------------------------------------------------------------------------------------------------------------------------| ------------------------------------------------------------------|
| `/entry` | `POST` | `plate`, `parkingLot` | `{"ticketId": "..."}`                                                                                                              | `400` if plate format is invalid<br>`409` if plate already inside |
| `/exit`  | `POST` | `ticketId`            | `{"licensePlate": "...", "totalParkedTime": ..., "parkingLot": "...", "charge": "..."}`                                            | `404` unknown ticket<br>`409` double exit                         |
| `/pay`   | `POST` | `ticketId`            | `{"ticketId": "...", "licensePlate": "...", "charged": "...", "currency": "...", "transactionId": "...", "payment_status": "paid"}`| `404` unknown ticket<br>`409` already paid                        |

---
