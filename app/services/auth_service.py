from typing import Optional
from datetime import datetime, timedelta
import secrets
from flask import current_app
from app import db
from app.models import User


class AuthService:

    SESSION_PREFIX = 'session:'
    SESSION_EXPIRY = 86400

    def register_user(self, username: str, email: str, password: str) -> User:
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        if not email or not email.strip():
            raise ValueError("Email cannot be empty")

        if not password or len(password) < 1:
            raise ValueError("Password cannot be empty")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            raise ValueError(f"Username '{username}' already exists")

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            raise ValueError(f"Email '{email}' already exists")

        user = User(
            username=username.strip(),
            email=email.strip(),
            is_author=False
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        if not username or not password:
            return None

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            return user

        return None

    def create_session(self, user: User) -> str:
        token = secrets.token_urlsafe(32)

        from app import redis_client

        session_key = f"{self.SESSION_PREFIX}{token}"
        redis_client.setex(
            session_key,
            self.SESSION_EXPIRY,
            str(user.id)
        )

        return token

    def validate_session(self, token: str) -> Optional[User]:
        if not token:
            return None

        from app import redis_client

        session_key = f"{self.SESSION_PREFIX}{token}"
        user_id_str = redis_client.get(session_key)

        if not user_id_str:
            return None

        try:
            user_id = int(user_id_str)
            user = User.query.get(user_id)
            return user
        except (ValueError, TypeError):
            return None

    def terminate_session(self, token: str) -> bool:
        if not token:
            return False

        from app import redis_client

        session_key = f"{self.SESSION_PREFIX}{token}"
        result = redis_client.delete(session_key)

        return result > 0

    def refresh_session(self, token: str) -> bool:
        if not token:
            return False

        from app import redis_client

        session_key = f"{self.SESSION_PREFIX}{token}"

        if not redis_client.exists(session_key):
            return False

        redis_client.expire(session_key, self.SESSION_EXPIRY)
        return True
