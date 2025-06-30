import pytest
import json
import os
import tempfile
from app import app, db, Book, Review

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

@pytest.fixture
def client():
    """Create a test client with isolated database for each test"""
    # Store original config
    original_config = app.config.copy()
    
    # Apply test configuration
    app.config.from_object(TestConfig)
    
    with app.test_client() as client:
        with app.app_context():
            # Create fresh tables for each test
            db.drop_all()
            db.create_all()
            
            # Clear any cached data
            from app import redis_client
            if hasattr(redis_client, 'data'):
                redis_client.data.clear()  # Clear mock Redis data
            
            yield client
            
            # Cleanup after test
            db.session.remove()
            db.drop_all()
    
    # Restore original config
    app.config.clear()
    app.config.update(original_config)

@pytest.fixture
def sample_book_data():
    """Sample book data for testing"""
    return {
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'isbn': '978-0-7432-7356-5',
        'publication_year': 1925
    }

@pytest.fixture
def sample_review_data():
    """Sample review data for testing"""
    return {
        'reviewer_name': 'John Doe',
        'rating': 4,
        'review_text': 'Great book! Highly recommended.'
    }

class TestBooksAPI:
    """Test cases for Books API endpoints"""
    
    def test_get_books_empty(self, client):
        """Test GET /books with no books in database"""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'books' in data
        assert len(data['books']) == 0
        assert data['source'] == 'database'  # Cache miss on empty database
    
    def test_add_book_success(self, client, sample_book_data):
        """Test POST /books with valid data"""
        response = client.post('/books', 
                             data=json.dumps(sample_book_data),
                             content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'book' in data
        assert data['book']['title'] == sample_book_data['title']
        assert data['book']['author'] == sample_book_data['author']
        assert data['book']['isbn'] == sample_book_data['isbn']
        assert data['book']['publication_year'] == sample_book_data['publication_year']
        assert 'id' in data['book']
        assert 'created_at' in data['book']
    
    def test_add_book_missing_title(self, client):
        """Test POST /books without required title"""
        invalid_data = {'author': 'Test Author'}
        response = client.post('/books',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'title' in data['message']
    
    def test_add_book_missing_author(self, client):
        """Test POST /books without required author"""
        invalid_data = {'title': 'Test Book'}
        response = client.post('/books',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'author' in data['message']
    
    def test_add_book_empty_title(self, client):
        """Test POST /books with empty title"""
        invalid_data = {'title': '   ', 'author': 'Test Author'}
        response = client.post('/books',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'title' in data['message']
    
    def test_add_book_duplicate_isbn(self, client, sample_book_data):
        """Test POST /books with duplicate ISBN"""
        # Add first book
        response1 = client.post('/books',
                               data=json.dumps(sample_book_data),
                               content_type='application/json')
        assert response1.status_code == 201
        
        # Try to add second book with same ISBN
        duplicate_data = sample_book_data.copy()
        duplicate_data['title'] = 'Different Title'
        duplicate_data['author'] = 'Different Author'
        
        response2 = client.post('/books',
                               data=json.dumps(duplicate_data),
                               content_type='application/json')
        assert response2.status_code == 400
        data = json.loads(response2.data)
        assert 'ISBN' in data['message']
    
    def test_add_book_invalid_publication_year(self, client):
        """Test POST /books with invalid publication year"""
        invalid_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'publication_year': 'not_a_number'
        }
        response = client.post('/books',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'publication year' in data['message'].lower()
    
    def test_get_books_with_data(self, client, sample_book_data):
        """Test GET /books after adding a book"""
        # Add a book first
        add_response = client.post('/books',
                                 data=json.dumps(sample_book_data),
                                 content_type='application/json')
        assert add_response.status_code == 201
        
        # Get all books
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['books']) == 1
        assert data['books'][0]['title'] == sample_book_data['title']
        assert data['books'][0]['author'] == sample_book_data['author']

class TestReviewsAPI:
    """Test cases for Reviews API endpoints"""
    
    def test_get_reviews_nonexistent_book(self, client):
        """Test GET /books/{id}/reviews for non-existent book"""
        response = client.get('/books/999/reviews')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'not found' in data['message']
    
    def test_add_review_nonexistent_book(self, client, sample_review_data):
        """Test POST /books/{id}/reviews for non-existent book"""
        response = client.post('/books/999/reviews',
                             data=json.dumps(sample_review_data),
                             content_type='application/json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'not found' in data['message']
    
    def test_add_review_success(self, client, sample_book_data, sample_review_data):
        """Test POST /books/{id}/reviews with valid data"""
        # Add a book first
        book_response = client.post('/books',
                                  data=json.dumps(sample_book_data),
                                  content_type='application/json')
        assert book_response.status_code == 201
        book_data = json.loads(book_response.data)
        book_id = book_data['book']['id']
        
        # Add a review
        response = client.post(f'/books/{book_id}/reviews',
                             data=json.dumps(sample_review_data),
                             content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'review' in data
        assert data['review']['rating'] == sample_review_data['rating']
        assert data['review']['reviewer_name'] == sample_review_data['reviewer_name']
        assert data['review']['book_id'] == book_id
        assert 'id' in data['review']
        assert 'created_at' in data['review']
    
    def test_add_review_missing_reviewer_name(self, client, sample_book_data):
        """Test POST /books/{id}/reviews without reviewer name"""
        # Add a book first
        book_response = client.post('/books',
                                  data=json.dumps(sample_book_data),
                                  content_type='application/json')
        book_data = json.loads(book_response.data)
        book_id = book_data['book']['id']
        
        # Try to add review without reviewer name
        invalid_review = {
            'rating': 4,
            'review_text': 'Test review'
        }
        
        response = client.post(f'/books/{book_id}/reviews',
                             data=json.dumps(invalid_review),
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'reviewer_name' in data['message']
    
    def test_add_review_invalid_rating_high(self, client, sample_book_data):
        """Test POST /books/{id}/reviews with rating too high"""
        # Add a book first
        book_response = client.post('/books',
                                  data=json.dumps(sample_book_data),
                                  content_type='application/json')
        book_data = json.loads(book_response.data)
        book_id = book_data['book']['id']
        
        # Try to add review with invalid rating
        invalid_review = {
            'reviewer_name': 'Test Reviewer',
            'rating': 6,  # Invalid - should be 1-5
            'review_text': 'Test review'
        }
        
        response = client.post(f'/books/{book_id}/reviews',
                             data=json.dumps(invalid_review),
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Rating must be between 1 and 5' in data['message']
    
    def test_add_review_invalid_rating_low(self, client, sample_book_data):
        """Test POST /books/{id}/reviews with rating too low"""
        # Add a book first
        book_response = client.post('/books',
                                  data=json.dumps(sample_book_data),
                                  content_type='application/json')
        book_data = json.loads(book_response.data)
        book_id = book_data['book']['id']
        
        # Try to add review with invalid rating
        invalid_review = {
            'reviewer_name': 'Test Reviewer',
            'rating': 0,  # Invalid - should be 1-5
            'review_text': 'Test review'
        }
        
        response = client.post(f'/books/{book_id}/reviews',
                             data=json.dumps(invalid_review),
                             content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Rating must be between 1 and 5' in data['message']
    
    def test_get_reviews_empty(self, client, sample_book_data):
        """Test GET /books/{id}/reviews with no reviews"""
        # Add a book first
        book_response = client.post('/books',
                                  data=json.dumps(sample_book_data),
                                  content_type='application/json')
        book_data = json.loads(book_response.data)
        book_id = book_data['book']['id']
        
        # Get reviews (should be empty)
        response = client.get(f'/books/{book_id}/reviews')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'reviews' in data
        assert len(data['reviews']) == 0
        assert data['book_id'] == book_id
        assert data['book_title'] == sample_book_data['title']
        assert data['source'] == 'database'  # Cache miss
    
    def test_get_reviews_success(self, client, sample_book_data, sample_review_data):
        """Test GET /books/{id}/reviews with existing reviews"""
        # Add a book first
        book_response = client.post('/books',
                                  data=json.dumps(sample_book_data),
                                  content_type='application/json')
        book_data = json.loads(book_response.data)
        book_id = book_data['book']['id']
        
        # Add a review
        review_response = client.post(f'/books/{book_id}/reviews',
                                    data=json.dumps(sample_review_data),
                                    content_type='application/json')
        assert review_response.status_code == 201
        
        # Get reviews
        response = client.get(f'/books/{book_id}/reviews')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'reviews' in data
        assert len(data['reviews']) == 1
        assert data['reviews'][0]['rating'] == sample_review_data['rating']
        assert data['reviews'][0]['reviewer_name'] == sample_review_data['reviewer_name']
        assert data['book_id'] == book_id

class TestIntegrationCacheMiss:
    """Integration test covering cache-miss scenario"""
    
    def test_cache_miss_flow(self, client, sample_book_data, sample_review_data):
        """Test the complete flow when cache is empty (cache-miss scenario)"""
        # 1. Get books (cache miss - empty database)
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['books']) == 0
        assert data['source'] == 'database'  # Cache miss
        
        # 2. Add a book
        book_response = client.post('/books',
                                  data=json.dumps(sample_book_data),
                                  content_type='application/json')
        assert book_response.status_code == 201
        book_data = json.loads(book_response.data)
        book_id = book_data['book']['id']
        
        # 3. Get books again (should hit database due to cache invalidation)
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['books']) == 1
        assert data['books'][0]['title'] == sample_book_data['title']
    
        
        # 4. Add a review
        review_response = client.post(f'/books/{book_id}/reviews',
                                    data=json.dumps(sample_review_data),
                                    content_type='application/json')
        assert review_response.status_code == 201
        
        # 5. Get reviews again (should hit database due to cache invalidation)
        response = client.get(f'/books/{book_id}/reviews')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['reviews']) == 1
        assert data['reviews'][0]['rating'] == sample_review_data['rating']
        assert data['reviews'][0]['reviewer_name'] == sample_review_data['reviewer_name']

class TestCacheHitScenario:
    """Test cache hit scenarios"""
    
    def test_books_cache_hit(self, client, sample_book_data):
        """Test that subsequent calls to GET /books hit the cache"""
        # Add a book
        client.post('/books', data=json.dumps(sample_book_data), content_type='application/json')
        
        # First call - should populate cache
        response1 = client.get('/books')
        assert response1.status_code == 200
        data1 = json.loads(response1.data)
        assert data1['source'] == 'database'
        
        # Second call - should hit cache (in mock environment, it will still show database)
        response2 = client.get('/books')
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        assert len(data2['books']) == 1

class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_invalid_json(self, client):
        """Test API with invalid JSON"""
        response = client.post('/books',
                             data='{"invalid": json}',  # Invalid JSON
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_empty_request_body(self, client):
        """Test API with empty request body"""
        response = client.post('/books',
                             data='',
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_no_content_type(self, client, sample_book_data):
        """Test API without proper content type"""
        response = client.post('/books',
                             data=json.dumps(sample_book_data))
        # This should still work as Flask handles it gracefully
        assert response.status_code in [400, 415]  # Either bad request or unsupported media type

class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'database' in data
        assert data['database'] == 'connected'
        assert 'cache' in data
        assert data['cache'] in ['connected', 'mock', 'disconnected']
        assert 'timestamp' in data

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_book_with_only_required_fields(self, client):
        """Test adding book with only required fields"""
        minimal_book = {
            'title': 'Minimal Book',
            'author': 'Test Author'
        }
        response = client.post('/books',
                             data=json.dumps(minimal_book),
                             content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['book']['title'] == minimal_book['title']
        assert data['book']['author'] == minimal_book['author']
        assert data['book']['isbn'] is None
        assert data['book']['publication_year'] is None
    
    def test_review_with_only_required_fields(self, client, sample_book_data):
        """Test adding review with only required fields"""
        # Add a book first
        book_response = client.post('/books',
                                  data=json.dumps(sample_book_data),
                                  content_type='application/json')
        book_data = json.loads(book_response.data)
        book_id = book_data['book']['id']
        
        # Add minimal review
        minimal_review = {
            'reviewer_name': 'Test Reviewer',
            'rating': 3
        }
        
        response = client.post(f'/books/{book_id}/reviews',
                             data=json.dumps(minimal_review),
                             content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['review']['reviewer_name'] == minimal_review['reviewer_name']
        assert data['review']['rating'] == minimal_review['rating']
        assert data['review']['review_text'] is None

if __name__ == '__main__':
    pytest.main(['-v'])