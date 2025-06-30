# Book Review Service

A comprehensive REST API for managing books and their reviews, built with Flask, SQLAlchemy, and Redis caching. Features include Swagger documentation, comprehensive testing, and optimized performance through caching.

## Features

- **Book Management**: Add and list books with metadata (title, author, ISBN, publication year)
- **Review System**: Add and retrieve reviews for books with ratings (1-5 stars)
- **Redis Caching**: Optimized performance with Redis-based caching
- **API Documentation**: Interactive Swagger UI documentation
- **Comprehensive Testing**: Full test suite with pytest
- **Database Migrations**: Flask-Migrate for database schema management
- **Health Monitoring**: Health check endpoint for system status

## Tech Stack

- **Backend**: Flask, SQLAlchemy
- **Database**: SQLite (development) / PostgreSQL (production)
- **Cache**: Redis
- **Documentation**: Flasgger (Swagger)
- **Testing**: pytest
- **Migrations**: Flask-Migrate

## Prerequisites

- Python 3.8+
- Redis Server
- pip (Python package manager)

## Quick Start

### 1. Clone and Setup

```bash
# Make setup script executable and run it
chmod +x setup.sh
./setup.sh
```

### 2. Start Redis Server

Before running the application, make sure Redis is running:

**On macOS (with Homebrew):**
```bash
brew services start redis
# or run in foreground
redis-server
```

**On Ubuntu/Debian:**
```bash
sudo systemctl start redis-server
# or
sudo service redis-server start
```

**On Windows:**
```bash
# Download and install Redis for Windows, then:
redis-server.exe
```

**Using Docker:**
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

### 3. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 4. Start the Application

```bash
python app.py
```

The service will be available at: `http://localhost:8000`

## Manual Setup (Alternative)

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Start the application
python app.py
```

## API Endpoints

### Books
- `GET /books` - List all books
- `POST /books` - Add a new book

### Reviews
- `GET /books/{id}/reviews` - Get reviews for a specific book
- `POST /books/{id}/reviews` - Add a review for a book

### System
- `GET /health` - Health check endpoint
- `GET /swagger/` - Interactive API documentation

## API Documentation

Once the service is running, visit `http://localhost:8000/swagger/` for interactive API documentation with Swagger UI.

## Testing

### Run All Tests
```bash
# Activate virtual environment first
source venv/bin/activate

# Run all tests with verbose output
pytest test_app.py -v

# Run tests with coverage
pytest test_app.py -v --cov=app
```

### Run Specific Test Categories
```bash
# Test only Books API
pytest test_app.py::TestBooksAPI -v

# Test only Reviews API
pytest test_app.py::TestReviewsAPI -v

# Test cache functionality
pytest test_app.py::TestCacheHitScenario -v

# Test error handling
pytest test_app.py::TestErrorHandling -v
```

### Test Coverage
```bash
# Install coverage if not already installed
pip install coverage

# Run tests with coverage report
pytest --cov=app --cov-report=html test_app.py

# View coverage report
open htmlcov/index.html
```

## Database Migrations

### Common Migration Commands

```bash
# Initialize migration repository (first time only)
flask db init

# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations to database
flask db upgrade

# Downgrade to previous migration
flask db downgrade

# Show current migration version
flask db current

# Show migration history
flask db history
```

### Migration Workflow

1. **Make model changes** in `app.py`
2. **Generate migration**: `flask db migrate -m "Description"`
3. **Review migration file** in `migrations/versions/`
4. **Apply migration**: `flask db upgrade`

## Demo Data

Populate the database with sample data for testing:

```bash
# Make sure the service is running first
python app.py &

# In another terminal, run the demo data script
python populate_demo_data.py
```

This will add:
- 5 sample books (classics like "The Great Gatsby", "1984", etc.)
- Multiple reviews for each book
- Demonstrates the full API functionality

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=sqlite:///book_reviews.db
# For PostgreSQL: DATABASE_URL=postgresql://user:password@localhost/book_reviews

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

### Production Configuration

For production deployment:

```bash
# Use PostgreSQL
DATABASE_URL=postgresql://user:password@host:port/database

# Use Redis with authentication
REDIS_URL=redis://:password@host:port/db

# Disable debugging
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_APP=app.py
```

## Caching Strategy

The service implements Redis caching with:

- **Cache TTL**: 30 seconds (configurable)
- **Cache Keys**: 
  - `books:all` - All books list
  - `reviews:book:{id}` - Reviews for specific book
- **Cache Invalidation**: Automatic on data modifications
- **Fallback**: Graceful degradation if Redis is unavailable

## Performance Optimization

- **Database Indexing**: Optimized queries with proper indexes
- **Connection Pooling**: SQLAlchemy connection pooling
- **Cache-First Strategy**: Redis cache reduces database load
- **Pagination Ready**: Structure supports future pagination implementation

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid input data
- **404 Not Found**: Resource doesn't exist
- **415 Unsupported Media Type**: Invalid content type
- **500 Internal Server Error**: Server-side errors

All errors return JSON responses with descriptive messages.

## Health Monitoring

Monitor service health:

```bash
curl http://localhost:8000/health
```

Response includes:
- Database connection status
- Redis cache connection status
- Current timestamp
- Overall system health

## Troubleshooting

### Common Issues

**1. Redis Connection Error**
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Start Redis if not running
redis-server
```

**2. Database Migration Errors**
```bash
# Reset migrations (careful - loses data)
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

**3. Port Already in Use**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

**4. Virtual Environment Issues**
```bash
# Recreate virtual environment
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Debug Mode

Enable detailed logging:

```python
# In app.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Usage Examples

### Add a Book
```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "isbn": "978-0-7432-7356-5",
    "publication_year": 1925
  }'
```

### Get All Books
```bash
curl http://localhost:8000/books
```

### Add a Review
```bash
curl -X POST http://localhost:8000/books/1/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_name": "John Doe",
    "rating": 5,
    "review_text": "Absolutely brilliant!"
  }'
```

### Get Book Reviews
```bash
curl http://localhost:8000/books/1/reviews
```

## Development

### Project Structure
```
book_review_service/
├── app.py                  # Main application file
├── test_app.py            # Test suite
├── populate_demo_data.py  # Demo data script
├── setup.sh               # Setup script
├── requirements.txt       # Python dependencies
├── migrations/            # Database migrations
├── venv/                  # Virtual environment
└── README.md             # This file
```