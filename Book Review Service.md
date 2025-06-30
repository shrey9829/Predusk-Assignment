# Book Review Service

A Flask-based RESTful API for managing books and their reviews, with SQLite database, Redis caching, and automated migrations.

## Features

- Add, list, and review books
- Caching with Redis for fast reads
- Database migrations with Alembic/Flask-Migrate
- OpenAPI/Swagger documentation via Flasgger
- Health check endpoint
- Automated tests with pytest

## Project Structure

```
.
├── app.py                  # Main Flask application
├── test_app.py             # Pytest test suite
├── populate_demo_data.py   # Script to populate demo data via API
├── requirements.txt        # Python dependencies
├── setup.sh                # Setup script (virtualenv, install, migrate)
├── .env                    # Environment variables
```

## Setup

1. **Clone the repository**  
   ```sh
   git clone <repo-url>
   cd <project-folder>
   ```

2. **Run the setup script**  
   ```sh
   bash setup.sh
   ```

   This will:
   - Create a virtual environment
   - Install dependencies
   - Initialize and migrate the database

3. **Run the application**  
   ```sh
   source venv/bin/activate
   python app.py
   ```

   The API will be available at [http://localhost:8000](http://localhost:8000).

4. **API Documentation**  
   Visit [http://localhost:8000/swagger/](http://localhost:8000/swagger/) for interactive API docs.

## Running Tests

```sh
source venv/bin/activate
pytest test_app.py -v
```

## Populating Demo Data

To populate the API with sample books and reviews:

```sh
python populate_demo_data.py
```

## API Endpoints

- `GET    /books`               - List all books
- `POST   /books`               - Add a new book
- `GET    /books/{id}/reviews`  - Get reviews for a book
- `POST   /books/{id}/reviews`  - Add a review for a book
- `GET    /health`              - Health check

## Environment Variables

Set in `.env` (loaded automatically):

```
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=sqlite:///book_reviews.db
```

## Notes

- By default, uses SQLite and expects Redis at `localhost:6379`.  
- If Redis is not available, caching will be skipped and a warning will be logged.
- Database migrations are managed with Flask-Migrate/Alembic.

---

**Author:**  
Book Review Service Team  
Contact: support@bookreviews.com