# Video Hosting Platform

A Flask-based video hosting platform with real-time co-viewing capabilities, channel management, and subscription features.

## Features

- **Video Management**: Upload, manage, and stream video content
- **Channel System**: Content creator profiles with subscriber management
- **Co-Viewing Rooms**: Watch videos together with synchronized playback
- **Real-Time Chat**: Live chat during co-viewing sessions
- **Subscription Tiers**: Regular subscriptions and sponsor-level memberships
- **Advertisement System**: Monetization through targeted ads (sponsors get ad-free experience)
- **WebSocket Support**: Real-time communication for chat and playback synchronization

## Technology Stack

- **Backend**: Flask 3.0, Python 3.8+
- **Database**: SQLAlchemy with SQLite (dev) / PostgreSQL (prod)
- **Real-Time**: Flask-SocketIO with Redis message queue
- **Caching**: Redis for session management and caching
- **Background Tasks**: Celery for video processing
- **Testing**: Pytest with Hypothesis for property-based testing

## Project Structure

```
video-hosting-platform/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models.py            # Database models
│   ├── api/                 # REST API endpoints
│   ├── services/            # Business logic services
│   └── websocket/           # WebSocket event handlers
├── tests/                   # Test suite
├── config.py                # Configuration classes
├── run.py                   # Application entry point
├── celery_worker.py         # Celery worker configuration
└── requirements.txt         # Python dependencies
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Redis server
- FFmpeg (for video processing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd video-hosting-platform
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**
   ```bash
   flask init-db
   ```

### Running the Application

#### Development Mode

1. **Start Redis server**
   ```bash
   redis-server
   ```

2. **Start the Flask application**
   ```bash
   python run.py
   ```

3. **Start Celery worker** (in a separate terminal)
   ```bash
   celery -A celery_worker.celery worker --loglevel=info
   ```

The application will be available at `http://localhost:5000`

#### Production Mode

For production deployment, use a WSGI server like Gunicorn with eventlet or gevent:

```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 run:app
```

## Configuration

Configuration is managed through environment variables. Key settings:

- `FLASK_ENV`: Environment (development/production/testing)
- `SECRET_KEY`: Secret key for session encryption
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- `UPLOAD_FOLDER`: Directory for video uploads
- `MAX_CONTENT_LENGTH`: Maximum upload size in bytes

See `.env.example` for all available configuration options.

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m property_test  # Property-based tests only
pytest -m integration    # Integration tests only
```

## API Documentation

API endpoints will be documented as they are implemented in subsequent tasks.

## Development Roadmap

- [x] Task 1: Project Setup and Core Infrastructure
- [ ] Task 2: Database Models and Migrations
- [ ] Task 3: Authentication and User Management
- [ ] Task 4: Channel Management
- [ ] Task 5: Video Management Core
- [ ] Task 6-24: Additional features (see tasks.md)

## License

[License information to be added]

## Contributing

[Contributing guidelines to be added]
