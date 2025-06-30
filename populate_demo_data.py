"""
Demo data population script for Book Review Service
Run this script to populate the database with sample data for testing
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

SAMPLE_BOOKS = [
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "isbn": "978-0-7432-7356-5",
        "publication_year": 1925
    },
    {
        "title": "To Kill a Mockingbird", 
        "author": "Harper Lee",
        "isbn": "978-0-06-112008-4",
        "publication_year": 1960
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "isbn": "978-0-452-28423-4",
        "publication_year": 1949
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "isbn": "978-0-14-143951-8", 
        "publication_year": 1813
    },
    {
        "title": "The Catcher in the Rye",
        "author": "J.D. Salinger",
        "isbn": "978-0-316-76948-0",
        "publication_year": 1951
    }
]

SAMPLE_REVIEWS = [
    ("Alice Johnson", 5, "Absolutely magnificent! A timeless classic that captures the essence of the American Dream."),
    ("Bob Smith", 4, "Great book, very engaging story. The symbolism is profound."),
    ("Carol Davis", 5, "One of the best books I've ever read. Highly recommend!"),
    ("David Wilson", 3, "Good book but a bit slow in places. Still worth reading."),
    ("Emma Brown", 4, "Beautiful prose and compelling characters. A must-read."),
    ("Frank Miller", 5, "Incredible storytelling. Every page is a masterpiece."),
    ("Grace Lee", 2, "Not my cup of tea. Found it hard to connect with the characters."),
    ("Henry Taylor", 4, "Well-written and thought-provoking. Great historical context."),
    ("Iris Anderson", 5, "Perfect blend of romance and social commentary."),
    ("Jack Thompson", 3, "Decent read but overhyped in my opinion.")
]

def check_service_health():
    """Check if the service is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def add_book(book_data):
    """Add a book to the service"""
    try:
        response = requests.post(
            f"{BASE_URL}/books",
            json=book_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 201:
            book_info = response.json()
            print(f"Added book: {book_data['title']} (ID: {book_info['book']['id']})")
            return book_info['book']['id']
        else:
            print(f"Failed to add book: {book_data['title']} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error adding book {book_data['title']}: {e}")
        return None

def add_review(book_id, reviewer_name, rating, review_text):
    """Add a review for a book"""
    review_data = {
        "reviewer_name": reviewer_name,
        "rating": rating,
        "review_text": review_text
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/books/{book_id}/reviews",
            json=review_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 201:
            print(f"Added review by {reviewer_name} for book ID {book_id} (Rating: {rating}/5)")
            return True
        else:
            print(f"Failed to add review by {reviewer_name}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error adding review by {reviewer_name}: {e}")
        return False

def get_books():
    """Get all books from the service"""
    try:
        response = requests.get(f"{BASE_URL}/books", timeout=10)
        if response.status_code == 200:
            return response.json()['books']
        else:
            print(f"Failed to get books: {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error getting books: {e}")
        return []

def get_book_reviews(book_id):
    """Get reviews for a specific book"""
    try:
        response = requests.get(f"{BASE_URL}/books/{book_id}/reviews", timeout=10)
        if response.status_code == 200:
            return response.json()['reviews']
        else:
            print(f"Failed to get reviews for book {book_id}: {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error getting reviews for book {book_id}: {e}")
        return []

def main():
    """Main function to populate demo data"""
    print("🚀 Book Review Service - Demo Data Population")
    print("=" * 50)
    
    # Check service health
    print("Checking service health...")
    if not check_service_health():
        print("Service is not running! Please start the service first.")
        print("   Run: python app.py")
        return
    print("Service is healthy and ready!")
    
    # Add books
    print("\nAdding sample books...")
    book_ids = []
    for book in SAMPLE_BOOKS:
        book_id = add_book(book)
        if book_id:
            book_ids.append(book_id)
        time.sleep(0.5)  # Small delay
    
    if not book_ids:
        print("No books were added successfully!")
        return
    
    print(f"\nSuccessfully added {len(book_ids)} books!")
    
    # Add reviews
    print("\nAdding sample reviews...")
    review_count = 0
    
    for i, book_id in enumerate(book_ids):
        num_reviews = min(3, len(SAMPLE_REVIEWS) - review_count)
        
        for j in range(num_reviews):
            if review_count < len(SAMPLE_REVIEWS):
                reviewer_name, rating, review_text = SAMPLE_REVIEWS[review_count]
                if add_review(book_id, reviewer_name, rating, review_text):
                    review_count += 1
                time.sleep(0.1)
    
    print(f"\nSuccessfully added {review_count} reviews!")
    
    print("\nDemo Data Summary:")
    print("=" * 30)
    
    books = get_books()
    total_reviews = 0
    
    for book in books:
        reviews = get_book_reviews(book['id'])
        total_reviews += len(reviews)
        avg_rating = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0
        
        print(f"{book['title']} by {book['author']}")
        print(f"   Reviews: {len(reviews)} | Average Rating: {avg_rating:.1f}/5")
    
    print(f"\nDemo data population complete!")
    print(f"   Total Books: {len(books)}")
    print(f"   Total Reviews: {total_reviews}")
    print(f"\nYou can now test the API at: {BASE_URL}")
    print("   Example: curl http://localhost:8000/books")

if __name__ == "__main__":
    main()