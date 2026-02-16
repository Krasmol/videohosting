# Project Setup Documentation

This document provides detailed information about the project setup and infrastructure for the Video Hosting Platform.

## Project Structure

```
video-hosting-platform/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory and initialization
│   ├── models.py                # Database models (to be implemented)
│   ├── api/                     # REST API endpoints
│   │   └── __init__.py
│   ├── services/                # Business logic services
│   │   └── __init__.py
│   └── websocket/               # WebSocket event handlers
│       └── __init__.py
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures and configuration
│   └── test_app_setup.py       # Application setup tests
├── uploads/                     # File uploads (created automatically)
│   ├── videos/                 # Video files
│   └── thumbnails/             # Video thumbnails
├── logs/                        # Application logs (created automatically)
├── config.py                    # Configuration classes
├── run.py                       # Application entry point
├── celery_worker.py            # Celery worker configuration
├── verify_setup.py             # Setup verification script
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── Makefile                    # Common commands
├── .env                        # Environment variables (local)
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

## Core Infrastructure Components

### 1. Flask Application Factory

**Location**: `app/__init__.py`

The application uses the factory pattern for creating Flask instances. This allows:
- Multiple configurations (development, production, testing)
- Easy testing with different configurations
- Proper extension initialization

**Key Functions**:
- `create_app(config_name)`: Creates and configures Flask application
- `initialize_extensions(app)`: Initializes all Flask extensions
- `setup_logging(app)`: Configures application logging
- `register_blueprints(app)`: Registers API blueprints
- `register_error_handlers(app)`: Sets up error handling

### 2. Configuration System

**Location**: `config.py`

Three configuration classes:
- **DevelopmentConfig**: Local development with debug mode
- **ProductionConfig**: Production deployment with security checks
- **TestingConfig**: Test environment with in-memory database

**Key Settings**:
- Database connection (SQLite for dev, PostgreSQL for prod)
- Redis URLs for caching and message queues
- File upload limits and allowed extensions
- Room configuration (participant limits, retention)
- Rate limiting settings
- Logging configuration

### 3. Database (SQLAlchemy)

**Extension**: Flask-SQLAlchemy
**Configuration**: Supports SQLite (dev) and PostgreSQL (prod)

**Features**:
- ORM for database operations
- Migration support (to be added)
- Relationship management
- Query optimization

### 4. WebSocket Support (Flask-SocketIO)

**Extension**: Flask-SocketIO with python-socketio
**Message Queue**: Redis for multi-instance support

**Features**:
- Real-time bidirectional communication
- Room-based message routing
- Event-driven architecture
- Scalable across multiple instances

### 5. Redis Integration

**Uses**:
1. **Session Management**: User session storage
2. **Caching**: Application-level caching
3. **Message Queue**: SocketIO message routing
4. **Celery Broker**: Background task queue
5. **Rate Limiting**: Request rate tracking

**Redis Databases** (by index):
- 0: Session storage and general caching
- 1: SocketIO message queue
- 2: Celery broker
- 3: Celery result backend
- 4: Rate limiting storage
- 10-14: Testing databases

### 6. Background Tasks (Celery)

**Location**: `celery_worker.py`
**Broker**: Redis

**Planned Tasks**:
- Video transcoding and processing
- Thumbnail generation
- Inactive room cleanup
- Notification delivery

**Start Worker**:
```bash
celery -A celery_worker.celery worker --loglevel=info
```

### 7. Authentication (Flask-Login)

**Extension**: Flask-Login
**Password Hashing**: bcrypt

**Features**:
- User session management
- Login/logout functionality
- Protected routes
- User loader callback

### 8. Rate Limiting (Flask-Limiter)

**Extension**: Flask-Limiter
**Storage**: Redis

**Configuration**:
- Default: 100 requests per hour
- Configurable per endpoint
- Different limits for authenticated users

### 9. CORS Support (Flask-CORS)

**Extension**: Flask-CORS

**Configuration**:
- Configurable allowed origins
- Supports credentials
- Preflight request handling

### 10. Logging Infrastructure

**Configuration**:
- Rotating file handler (10MB per file, 10 backups)
- Configurable log levels (DEBUG, INFO, WARN, ERROR)
- Structured log format with timestamps
- Separate log files for different environments

**Log Format**:
```
%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]
```

## Environment Variables

All configuration is managed through environment variables defined in `.env`:

### Flask Core
- `FLASK_APP`: Application entry point (run.py)
- `FLASK_ENV`: Environment (development/production/testing)
- `SECRET_KEY`: Session encryption key

### Database
- `DATABASE_URL`: Database connection string

### Redis
- `REDIS_URL`: Main Redis connection
- `SOCKETIO_MESSAGE_QUEUE`: SocketIO Redis URL
- `CELERY_BROKER_URL`: Celery broker URL
- `CELERY_RESULT_BACKEND`: Celery results URL
- `RATELIMIT_STORAGE_URL`: Rate limiting Redis URL

### File Uploads
- `UPLOAD_FOLDER`: Video upload directory
- `THUMBNAIL_FOLDER`: Thumbnail directory
- `MAX_CONTENT_LENGTH`: Maximum upload size (bytes)
- `ALLOWED_EXTENSIONS`: Allowed video formats

### Room Configuration
- `DEFAULT_MAX_PARTICIPANTS`: Non-sponsor room limit (10)
- `SPONSOR_MAX_PARTICIPANTS`: Sponsor room limit (-1 = unlimited)
- `INACTIVE_ROOM_RETENTION_HOURS`: Room data retention (24)

### Logging
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `LOG_FILE`: Log file path

## Error Handling

### HTTP Error Handlers

All HTTP errors return JSON responses in standard format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

**Registered Error Codes**:
- 400: BAD_REQUEST
- 401: UNAUTHORIZED
- 403: FORBIDDEN
- 404: NOT_FOUND
- 409: CONFLICT
- 422: UNPROCESSABLE_ENTITY
- 429: RATE_LIMIT_EXCEEDED
- 500: INTERNAL_SERVER_ERROR
- 503: SERVICE_UNAVAILABLE

### WebSocket Error Handling

WebSocket errors are emitted as events:

```json
{
  "event": "error",
  "data": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "recoverable": true/false
  }
}
```

## Testing Infrastructure

### Test Configuration

**Framework**: pytest with plugins
**Coverage**: pytest-cov
**Property Testing**: Hypothesis

**Pytest Plugins**:
- pytest-flask: Flask testing utilities
- pytest-flask-sqlalchemy: Database testing
- pytest-cov: Coverage reporting
- pytest-mock: Mocking support
- hypothesis: Property-based testing

### Test Categories

**Markers**:
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.property_test`: Property-based tests
- `@pytest.mark.websocket`: WebSocket tests
- `@pytest.mark.slow`: Long-running tests

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific category
pytest -m unit
pytest -m property_test

# Specific file
pytest tests/test_app_setup.py

# Verbose output
pytest -v
```

### Test Fixtures

**Location**: `tests/conftest.py`

**Available Fixtures**:
- `app`: Flask application instance
- `client`: Test client for HTTP requests
- `db_session`: Database session with auto-cleanup
- `socketio_client`: SocketIO test client
- `runner`: CLI test runner

## Verification and Validation

### Setup Verification Script

**Location**: `verify_setup.py`

Checks:
1. Python version (3.8+)
2. Required dependencies installed
3. Redis connection (optional)
4. Environment configuration
5. Directory structure
6. Flask application creation

**Run**:
```bash
python verify_setup.py
```

### Initial Setup Tests

**Location**: `tests/test_app_setup.py`

**Test Suites**:
1. **TestApplicationSetup**: Application initialization
2. **TestConfiguration**: Configuration settings
3. **TestHealthCheck**: Basic health checks

**Coverage**: 75% of core application code

## Common Commands

### Using Makefile

```bash
make help       # Show available commands
make install    # Install dependencies
make setup      # Initial setup
make verify     # Verify setup
make run        # Run development server
make worker     # Run Celery worker
make test       # Run tests
make test-cov   # Run tests with coverage
make init-db    # Initialize database
make clean      # Clean generated files
```

### Manual Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python run.py

# Run Celery worker
celery -A celery_worker.celery worker --loglevel=info

# Initialize database
flask init-db

# Run tests
pytest
pytest --cov=app --cov-report=html

# Clean up
find . -type d -name "__pycache__" -exec rm -rf {} +
```

## Security Considerations

### Development vs Production

**Development**:
- Debug mode enabled
- SQLite database
- Verbose logging
- CORS allows all origins
- Default secret key

**Production**:
- Debug mode disabled
- PostgreSQL database required
- INFO level logging
- Restricted CORS origins
- Strong secret key required
- HTTPS recommended
- Rate limiting enforced

### Best Practices

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Use strong SECRET_KEY** - Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
3. **Enable HTTPS in production** - Use reverse proxy (nginx/Apache)
4. **Restrict CORS origins** - Only allow trusted domains
5. **Use PostgreSQL in production** - SQLite not suitable for concurrent access
6. **Monitor rate limits** - Adjust based on usage patterns
7. **Regular security updates** - Keep dependencies updated

## Next Steps

After completing Task 1 (Project Setup), the following tasks will implement:

1. **Task 2**: Database models and migrations
2. **Task 3**: Authentication and user management
3. **Task 4**: Channel management
4. **Task 5**: Video management core
5. **Task 6+**: Additional features (rooms, chat, subscriptions, etc.)

Each task builds on the infrastructure established in this setup phase.

## Troubleshooting

### Common Issues

**1. Redis Connection Failed**
- Ensure Redis is installed and running: `redis-server`
- Check Redis URL in `.env`
- For testing, Redis is optional

**2. Import Errors**
- Verify virtual environment is activated
- Run `pip install -r requirements.txt`
- Check Python version (3.8+)

**3. Database Errors**
- Run `flask init-db` to initialize database
- Check DATABASE_URL in `.env`
- Ensure write permissions for SQLite file

**4. Port Already in Use**
- Change port in `run.py` or use environment variable
- Kill existing process: `lsof -ti:5000 | xargs kill` (Unix)

**5. Test Failures**
- Ensure test database is clean
- Check Redis is running (for integration tests)
- Run tests in isolation: `pytest tests/test_app_setup.py`

## Support and Documentation

- **Requirements**: `.kiro/specs/video-hosting-platform/requirements.md`
- **Design**: `.kiro/specs/video-hosting-platform/design.md`
- **Tasks**: `.kiro/specs/video-hosting-platform/tasks.md`
- **README**: `README.md`
- **This Document**: `SETUP.md`

For questions or issues, refer to the specification documents or run the verification script.
