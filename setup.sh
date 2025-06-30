#!/bin/bash

# setup.sh - Setup script for Book Review Service

echo "Setting up Book Review Service..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
flask db init || echo "Database already initialized"
flask db migrate -m "Initial migration" || echo "Migration already exists"
flask db upgrade

echo "Setup complete!"
echo ""
echo "To run the application:"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
echo "To run tests:"
echo "  source venv/bin/activate"
echo "  pytest test_app.py -v"
echo ""
echo "API Endpoints:"
echo "  GET    /books               - List all books"
echo "  POST   /books               - Add a new book"
echo "  GET    /books/{id}/reviews  - Get reviews for a book"
echo "  POST   /books/{id}/reviews  - Add a review for a book"