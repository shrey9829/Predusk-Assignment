# app.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_migrate import Migrate
import redis
import json
from datetime import datetime, timezone
from typing import List, Optional
import os
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
from flasgger import Swagger

app = Flask(__name__)

# Swagger Configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger/"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Book Reviews API",
        "description": "A comprehensive API for managing books and their reviews with Redis caching",
        "version": "1.0.0",
        "contact": {
            "name": "API Support",
            "email": "support@bookreviews.com"
        }
    },
    "host": "localhost:8000",
    "basePath": "/",
    "schemes": ["http", "https"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "tags": [
        {
            "name": "Books",
            "description": "Operations related to book management"
        },
        {
            "name": "Reviews",
            "description": "Operations related to book reviews"
        },
        {
            "name": "Health",
            "description": "System health check endpoints"
        }
    ]
}
swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///book_reviews.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Redis Configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Redis
try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
except redis.exceptions.ConnectionError:
      app.logger.error("Reddis server not connected")

# Models
class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    publication_year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship with reviews
    reviews = db.relationship('Review', backref='book', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'publication_year': self.publication_year,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    reviewer_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Index for optimizing reviews by book queries
    __table_args__ = (db.Index('idx_reviews_book_id', 'book_id'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'book_id': self.book_id,
            'reviewer_name': self.reviewer_name,
            'rating': self.rating,
            'review_text': self.review_text,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

#v Redis Cache keys
BOOKS_CACHE_KEY = "books:all"
BOOK_CACHE_KEY_PREFIX = "book:"
REVIEWS_CACHE_KEY_PREFIX = "reviews:book:"

# Redis Cache helper functions
def get_from_cache(key: str):
    ttl = redis_client.ttl(BOOKS_CACHE_KEY)
    print(f"TTL: {ttl}") 
    try:
        cached_data = redis_client.get(key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        app.logger.warning(f"Cache read error: {e}")
    return None

def set_cache(key: str, data, expire_time: int = 10):
    try:
        redis_client.setex(key, expire_time, json.dumps(data, default=str))
    except Exception as e:
        app.logger.warning(f"Cache write error: {e}")

def invalidate_cache(pattern: str):
    try:
        if hasattr(redis_client, 'delete'):
            redis_client.delete(pattern)
    except Exception as e:
        app.logger.warning(f"Cache invalidation error: {e}")

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found', 'message': str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500

# API Routes
@app.route('/books', methods=['GET'])
def get_books():
    """
    Get all books
    ---
    tags:
      - Books
    summary: List all books
    description: Retrieve a list of all books in the database with caching support
    responses:
      200:
        description: Successfully retrieved books
        schema:
          type: object
          properties:
            books:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: Unique book identifier
                    example: 1
                  title:
                    type: string
                    description: Book title
                    example: "The Great Gatsby"
                  author:
                    type: string
                    description: Book author
                    example: "F. Scott Fitzgerald"
                  isbn:
                    type: string
                    description: Book ISBN (optional)
                    example: "978-0-7432-7356-5"
                  publication_year:
                    type: integer
                    description: Year of publication (optional)
                    example: 1925
                  created_at:
                    type: string
                    format: date-time
                    description: Creation timestamp
                    example: "2023-01-15T10:30:00+00:00"
            source:
              type: string
              description: Data source (cache or database)
              example: "cache"
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Internal server error"
            message:
              type: string
              example: "An unexpected error occurred"
    """
    try:
        # Try to get from cache first
        cached_books = get_from_cache(BOOKS_CACHE_KEY)
        if cached_books is not None:
            return jsonify({'books': cached_books, 'source': 'cache'})
        
        # Cache miss - fetch from database
        books = db.session.execute(db.select(Book)).scalars().all()
        books_data = [book.to_dict() for book in books]
        
        # Populate cache
        set_cache(BOOKS_CACHE_KEY, books_data)
        
        return jsonify({'books': books_data, 'source': 'database'})
    
    except Exception as e:
        app.logger.error(f"Error fetching books: {e}")
        raise InternalServerError("Failed to fetch books")

@app.route('/books', methods=['POST'])
def add_book():
    """
    Add a new book
    ---
    tags:
      - Books
    summary: Create a new book
    description: Add a new book to the database
    parameters:
      - in: body
        name: book
        description: Book object to be created
        required: true
        schema:
          type: object
          required:
            - title
            - author
          properties:
            title:
              type: string
              description: Book title
              example: "To Kill a Mockingbird"
            author:
              type: string
              description: Book author
              example: "Harper Lee"
            isbn:
              type: string
              description: Book ISBN (optional)
              example: "978-0-06-112008-4"
            publication_year:
              type: integer
              description: Year of publication (optional)
              example: 1960
    responses:
      201:
        description: Book created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Book added successfully"
            book:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                title:
                  type: string
                  example: "To Kill a Mockingbird"
                author:
                  type: string
                  example: "Harper Lee"
                isbn:
                  type: string
                  example: "978-0-06-112008-4"
                publication_year:
                  type: integer
                  example: 1960
                created_at:
                  type: string
                  format: date-time
                  example: "2023-01-15T10:30:00+00:00"
      400:
        description: Bad request - validation error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Bad request"
            message:
              type: string
              example: "'title' is required and cannot be empty"
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Internal server error"
            message:
              type: string
              example: "An unexpected error occurred"
    """
    if not request.is_json:
        return jsonify({'error': 'Unsupported Media Type. Content-Type must be application/json'}), 415
    
    try:
        data = request.get_json()
        
        if not data:
            raise BadRequest("No JSON data provided")
        
        # Validate required fields
        required_fields = ['title', 'author']
        for field in required_fields:
            if field not in data or not data[field].strip():
                raise BadRequest(f"'{field}' is required and cannot be empty")
        
        # Validate rating if provided
        if 'publication_year' in data and data['publication_year']:
            try:
                year = int(data['publication_year'])
                if year < 0 or year > datetime.now(timezone.utc).year + 1:
                    raise BadRequest("Invalid publication year")
                data['publication_year'] = year
            except ValueError:
                raise BadRequest("Publication year must be a valid integer")
        
        # Check for duplicate ISBN if provided
        if data.get('isbn'):
            existing_book = Book.query.filter_by(isbn=data['isbn']).first()
            if existing_book:
                raise BadRequest(f"Book with ISBN '{data['isbn']}' already exists")
        
        # Create new book
        book = Book(
            title=data['title'].strip(),
            author=data['author'].strip(),
            isbn=data.get('isbn', '').strip() or None,
            publication_year=data.get('publication_year')
        )
        
        db.session.add(book)
        db.session.commit()
        
        # Invalidate books cache
        invalidate_cache(BOOKS_CACHE_KEY)
        
        return jsonify({
            'message': 'Book added successfully',
            'book': book.to_dict()
        }), 201
    
    except BadRequest:
        raise
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding book: {e}")
        raise InternalServerError("Failed to add book")

@app.route('/books/<int:book_id>/reviews', methods=['GET'])
def get_book_reviews(book_id: int):
    """
    Get all reviews for a specific book
    ---
    tags:
      - Reviews
    summary: List reviews for a book
    description: Retrieve all reviews for a specific book with caching support
    parameters:
      - in: path
        name: book_id
        type: integer
        required: true
        description: Unique book identifier
        example: 1
    responses:
      200:
        description: Successfully retrieved reviews
        schema:
          type: object
          properties:
            book_id:
              type: integer
              description: Book identifier
              example: 1
            book_title:
              type: string
              description: Book title
              example: "The Great Gatsby"
            reviews:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: Review identifier
                    example: 1
                  book_id:
                    type: integer
                    description: Book identifier
                    example: 1
                  reviewer_name:
                    type: string
                    description: Name of the reviewer
                    example: "John Doe"
                  rating:
                    type: integer
                    description: Rating (1-5 stars)
                    example: 5
                  review_text:
                    type: string
                    description: Review content (optional)
                    example: "An amazing classic that everyone should read!"
                  created_at:
                    type: string
                    format: date-time
                    description: Review creation timestamp
                    example: "2023-01-15T10:30:00+00:00"
            source:
              type: string
              description: Data source (cache or database)
              example: "cache"
      404:
        description: Book not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Resource not found"
            message:
              type: string
              example: "Book with id 1 not found"
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Internal server error"
            message:
              type: string
              example: "An unexpected error occurred"
    """
    try:
        # Check if book exists
        book = db.session.get(Book, book_id)
        if not book:
            raise NotFound(f"Book with id {book_id} not found")
        
        # Try cache first
        cache_key = f"{REVIEWS_CACHE_KEY_PREFIX}{book_id}"
        cached_reviews = get_from_cache(cache_key)
        if cached_reviews is not None:
            return jsonify({
                'book_id': book_id,
                'book_title': book.title,
                'reviews': cached_reviews,
                'source': 'cache'
            })
        
        # Cache miss - fetch from database using optimized query with index
        reviews = Review.query.filter_by(book_id=book_id).order_by(Review.created_at.desc()).all()
        reviews_data = [review.to_dict() for review in reviews]
        
        # Populate cache
        set_cache(cache_key, reviews_data)
        
        return jsonify({
            'book_id': book_id,
            'book_title': book.title,
            'reviews': reviews_data,
            'source': 'database'
        })
    
    except NotFound:
        raise
    except Exception as e:
        app.logger.error(f"Error fetching reviews for book {book_id}: {e}")
        raise InternalServerError("Failed to fetch reviews")

@app.route('/books/<int:book_id>/reviews', methods=['POST'])
def add_book_review(book_id: int):
    """
    Add a review for a specific book
    ---
    tags:
      - Reviews
    summary: Create a new review
    description: Add a new review for a specific book
    parameters:
      - in: path
        name: book_id
        type: integer
        required: true
        description: Unique book identifier
        example: 1
      - in: body
        name: review
        description: Review object to be created
        required: true
        schema:
          type: object
          required:
            - reviewer_name
            - rating
          properties:
            reviewer_name:
              type: string
              description: Name of the reviewer
              example: "Jane Smith"
            rating:
              type: integer
              description: Rating (1-5 stars)
              minimum: 1
              maximum: 5
              example: 4
            review_text:
              type: string
              description: Review content (optional)
              example: "Great book with compelling characters and plot!"
    responses:
      201:
        description: Review created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Review added successfully"
            review:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                book_id:
                  type: integer
                  example: 1
                reviewer_name:
                  type: string
                  example: "Jane Smith"
                rating:
                  type: integer
                  example: 4
                review_text:
                  type: string
                  example: "Great book with compelling characters and plot!"
                created_at:
                  type: string
                  format: date-time
                  example: "2023-01-15T10:30:00+00:00"
      400:
        description: Bad request - validation error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Bad request"
            message:
              type: string
              example: "Rating must be between 1 and 5"
      404:
        description: Book not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Resource not found"
            message:
              type: string
              example: "Book with id 1 not found"
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Internal server error"
            message:
              type: string
              example: "An unexpected error occurred"
    """
    try:
        # Check if book exists
        book = db.session.get(Book, book_id)
        if not book:
            raise NotFound(f"Book with id {book_id} not found")
        
        data = request.get_json()
        if not data:
            raise BadRequest("No JSON data provided")
        
        # Validate required fields
        required_fields = ['reviewer_name', 'rating']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f"'{field}' is required")
        
        # Validate reviewer name
        if not data['reviewer_name'].strip():
            raise BadRequest("Reviewer name cannot be empty")
        
        # Validate rating
        try:
            rating = int(data['rating'])
            if rating < 1 or rating > 5:
                raise BadRequest("Rating must be between 1 and 5")
        except (ValueError, TypeError):
            raise BadRequest("Rating must be a valid integer between 1 and 5")
        
        # Create new review
        review = Review(
            book_id=book_id,
            reviewer_name=data['reviewer_name'].strip(),
            rating=rating,
            review_text=data.get('review_text', '').strip() or None
        )
        
        db.session.add(review)
        db.session.commit()
        
        # Invalidate relevant caches
        cache_key = f"{REVIEWS_CACHE_KEY_PREFIX}{book_id}"
        invalidate_cache(cache_key)
        
        return jsonify({
            'message': 'Review added successfully',
            'review': review.to_dict()
        }), 201
    
    except (NotFound, BadRequest):
        raise
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding review for book {book_id}: {e}")
        raise InternalServerError("Failed to add review")

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    ---
    tags:
      - Health
    summary: System health check
    description: Check the health status of the API, database, and cache connections
    responses:
      200:
        description: System is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: "healthy"
            database:
              type: string
              example: "connected"
            cache:
              type: string
              example: "connected"
            timestamp:
              type: string
              format: date-time
              example: "2023-01-15T10:30:00+00:00"
      500:
        description: System is unhealthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: "unhealthy"
            error:
              type: string
              example: "Database connection failed"
            timestamp:
              type: string
              format: date-time
              example: "2023-01-15T10:30:00+00:00"
    """
    try:
        db.session.execute(text('SELECT 1'))
        
        cache_status = "connected"
        try:
            if hasattr(redis_client, 'ping'):
                redis_client.ping()
            else:
                cache_status = "mock"
        except:
            cache_status = "disconnected"
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'cache': cache_status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

# Initialize database tables
def init_db():
    """Initialize database tables"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    # Initialize database when running directly
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8000)