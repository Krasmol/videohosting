import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_session import Session
from flask_cors import CORS
from flask_marshmallow import Marshmallow
import redis

from config import config

db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()
session = Session()
ma = Marshmallow()
redis_client = None


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if config_name == 'production':
        config[config_name].init_app(app)

    initialize_extensions(app)

    setup_logging(app)

    register_blueprints(app)

    register_error_handlers(app)

    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.now().year}

    create_directories(app)

    # Quick SQLite schema self-heal for dev/demo installs.
    # If the DB was created with an older schema, new columns (e.g. is_moderator)
    # are missing and *any* auth query will crash with "no such column".
    # We keep this narrowly scoped to SQLite.
    with app.app_context():
        try:
            # Make sure all models are imported before calling create_all()/migrations.
            # Otherwise SQLAlchemy may not know about the tables yet and won't create them.
            from app import models  # noqa: F401
            from app.schema_migration import ensure_sqlite_schema
            ensure_sqlite_schema(app)
        except Exception as e:
            app.logger.warning(f'Schema migration skipped/failed: {e}')

    with app.app_context():
        from app import websocket

    app.logger.info(f'Video hosting platform started with {config_name} configuration')

    return app


def initialize_extensions(app):
    global redis_client

    db.init_app(app)

    ma.init_app(app)

    redis_available = False
    try:
        redis_client = redis.from_url(app.config['REDIS_URL'])
        redis_client.ping()
        redis_available = True
        app.logger.info('Connected to Redis')
    except Exception as e:
        app.logger.warning(f'Redis not available, using in-memory storage: {e}')
        import fakeredis
        redis_client = fakeredis.FakeStrictRedis()

    app.config['SESSION_REDIS'] = redis_client
    session.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    mq = app.config['SOCKETIO_MESSAGE_QUEUE'] if redis_available else None

    socketio.init_app(
        app,
        message_queue=mq,
        async_mode=app.config['SOCKETIO_ASYNC_MODE'],
        cors_allowed_origins=app.config['CORS_ORIGINS']
    )

    CORS(app, origins=app.config['CORS_ORIGINS'])

    app.logger.info('Extensions initialized successfully')


def setup_logging(app):
    if not app.debug and not app.testing:
        log_dir = os.path.dirname(app.config['LOG_FILE'])
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=10485760,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)

    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    app.logger.info('Logging configured')


def register_blueprints(app):
    from app.routes import web_bp
    from app.api.auth import auth_bp
    from app.api.channels import channels_bp
    from app.api.videos import videos_bp
    from app.api.subscriptions import subscriptions_bp
    from app.api.rooms import rooms_bp
    from app.api.admin import admin_bp
    from app.api.notifications import notifications_bp
    from app.api.messages import messages_bp
    from app.api.reactions import reactions_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(channels_bp, url_prefix='/api/channels')
    app.register_blueprint(videos_bp, url_prefix='/api/videos')
    app.register_blueprint(subscriptions_bp, url_prefix='/api')
    app.register_blueprint(rooms_bp, url_prefix='/api/rooms')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(messages_bp, url_prefix='/api/messages')
    app.register_blueprint(reactions_bp, url_prefix='/api')

    app.logger.info('Blueprints registered')


def register_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(error):
        return {
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'The request could not be understood or was missing required parameters.'
            }
        }, 400

    @app.errorhandler(401)
    def unauthorized(error):
        return {
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Authentication is required to access this resource.'
            }
        }, 401

    @app.errorhandler(403)
    def forbidden(error):
        return {
            'error': {
                'code': 'FORBIDDEN',
                'message': 'You do not have permission to access this resource.'
            }
        }, 403

    @app.errorhandler(404)
    def not_found(error):
        return {
            'error': {
                'code': 'NOT_FOUND',
                'message': 'The requested resource was not found.'
            }
        }, 404

    @app.errorhandler(409)
    def conflict(error):
        return {
            'error': {
                'code': 'CONFLICT',
                'message': 'The request conflicts with the current state of the resource.'
            }
        }, 409

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return {
            'error': {
                'code': 'UNPROCESSABLE_ENTITY',
                'message': 'The request was well-formed but contains invalid data.'
            }
        }, 422

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f'Internal server error: {error}')
        return {
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An internal server error occurred. Please try again later.'
            }
        }, 500

    @app.errorhandler(503)
    def service_unavailable(error):
        return {
            'error': {
                'code': 'SERVICE_UNAVAILABLE',
                'message': 'The service is temporarily unavailable. Please try again later.'
            }
        }, 503

    app.logger.info('Error handlers registered')


def create_directories(app):
    # Ensure folders exist for uploads, thumbnails, logs and the Flask instance dir (SQLite DB default).
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['THUMBNAIL_FOLDER'],
        os.path.dirname(app.config['LOG_FILE']),
        app.instance_path,
    ]

    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            app.logger.info(f'Created directory: {directory}')


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
