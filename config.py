# Видеохостинг - учебный проект группы [ИСП 33-9]
# Copyright (C) [2026] [Иван, Дмитрий, Роман, Савелий, Арсений, Кирилл]
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _abs_path(path: str) -> str:
    if not path:
        return path
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


class Config:

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Keep SQLite DB location stable regardless of the current working directory.
    # By default we store it under ./instance/video_platform.db
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL')
        or f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'video_platform.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'video_platform:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    UPLOAD_FOLDER = _abs_path(os.environ.get('UPLOAD_FOLDER') or os.path.join('uploads', 'videos'))
    THUMBNAIL_FOLDER = _abs_path(os.environ.get('THUMBNAIL_FOLDER') or os.path.join('uploads', 'thumbnails'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 524288000))
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

    VIDEO_PROCESSING_ENABLED = os.environ.get('VIDEO_PROCESSING_ENABLED', 'True').lower() == 'true'

    SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE') or 'redis://localhost:6379/1'
    SOCKETIO_ASYNC_MODE = os.environ.get('SOCKETIO_ASYNC_MODE') or 'threading'

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/2'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/3'

    DEFAULT_MAX_PARTICIPANTS = int(os.environ.get('DEFAULT_MAX_PARTICIPANTS', 10))
    SPONSOR_MAX_PARTICIPANTS = int(os.environ.get('SPONSOR_MAX_PARTICIPANTS', -1))
    INACTIVE_ROOM_RETENTION_HOURS = int(os.environ.get('INACTIVE_ROOM_RETENTION_HOURS', 24))

    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL') or 'redis://localhost:6379/4'
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT') or '100 per hour'

    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')


class DevelopmentConfig(Config):

    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):

    DEBUG = False
    TESTING = False

    @classmethod
    def init_app(cls, app):
        if app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
            raise ValueError('SECRET_KEY must be set in production')

        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            raise ValueError('SQLite should not be used in production')


class TestingConfig(Config):

    TESTING = True
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    WTF_CSRF_ENABLED = False

    REDIS_URL = 'redis://localhost:6379/10'
    SOCKETIO_MESSAGE_QUEUE = 'redis://localhost:6379/11'
    CELERY_BROKER_URL = 'redis://localhost:6379/12'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/13'
    RATELIMIT_STORAGE_URL = 'redis://localhost:6379/14'

    RATELIMIT_ENABLED = False

    VIDEO_PROCESSING_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
