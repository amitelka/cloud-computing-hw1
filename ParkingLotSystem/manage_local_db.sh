#!/bin/bash
# This script helps manage local DynamoDB tables for development

set -e

echo "DynamoDB Local Management Tool"
echo "==========================="
echo "1. List all tables"
echo "2. Delete a table"
echo "3. Create the parking-tickets table"
echo "4. Scan table contents"
echo "5. Exit"
echo ""

read -p "Enter your choice (1-5): " choice

case $choice in
  1)
    echo -e "\nListing all tables..."
    aws dynamodb list-tables --endpoint-url http://localhost:8000
    ;;
  2)
    read -p "Enter table name to delete: " tableName
    echo "Deleting table $tableName..."
    
    aws dynamodb delete-table --table-name $tableName --endpoint-url http://localhost:8000 && \
    echo "Table deleted successfully"
    ;;
  3)
    echo -e "\nCreating parking-tickets table..."
    
    aws dynamodb create-table \
      --cli-input-json file://deploy/create_table.json \
      --endpoint-url http://localhost:8000 && \
    echo "Table created successfully"
    ;;
  4)
    read -p "Enter table name to scan: " tableName
    echo "Scanning table $tableName..."
    
    aws dynamodb scan --table-name $tableName --endpoint-url http://localhost:8000
    ;;
  5)
    echo "Exiting..."
    exit 0
    ;;
  *)
    echo "Invalid choice. Please try again."
    ;;
esac

echo -e "\nDone."
