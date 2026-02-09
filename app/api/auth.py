import re
import string
import secrets
import random
from flask import Blueprint, request, jsonify
from app import db
from app.services.auth_service import AuthService
from app.models import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

FORBIDDEN_CHARS = re.compile(r'[^a-zA-Z0-9_.]')
PASSWORD_FORBIDDEN = re.compile(r'[<>\"\';&|`${}()\[\]]')


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Authorization header is required'}}), 401
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid authorization header format'}}), 401
        token = parts[1]
        user = auth_service.validate_session(token)
        if not user:
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid or expired session token'}}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.current_user.is_admin:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Admin access required'}}), 403
        return f(*args, **kwargs)
    return decorated_function


def require_moderator(f):
    """Allows moderators and admins."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = request.current_user
        if not (user.is_admin or getattr(user, 'is_moderator', False)):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Moderator access required'}}), 403
        return f(*args, **kwargs)
    return decorated_function


def validate_username(username):
    if not username or len(username) < 3 or len(username) > 30:
        return 'Username must be 3-30 characters'
    if FORBIDDEN_CHARS.search(username):
        return 'Username can only contain letters, numbers, underscores and dots'
    return None


def validate_password(password):
    if not password or len(password) < 6:
        return 'Password must be at least 6 characters'
    if PASSWORD_FORBIDDEN.search(password):
        return 'Password contains forbidden special characters'
    return None


def check_password_strength(password):
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[0-9]', password):
        score += 1
    if re.search(r'[!@#$%^&*\-_+=?/\\~]', password):
        score += 1

    if score <= 2:
        return 'weak'
    elif score <= 4:
        return 'medium'
    return 'strong'


def generate_login_code():
    while True:
        code = str(random.randint(1000, 9999))
        existing = User.query.filter_by(login_code=code).first()
        if not existing:
            return code


def generate_password(length=20):
    special = '!@#$%^&*-_+=?'
    chars = string.ascii_letters + string.digits + special
    pwd = []
    for _ in range(3):
        pwd.append(secrets.choice(string.ascii_lowercase))
    for _ in range(3):
        pwd.append(secrets.choice(string.ascii_uppercase))
    for _ in range(3):
        pwd.append(secrets.choice(string.digits))
    for _ in range(3):
        pwd.append(secrets.choice(special))
    pwd += [secrets.choice(chars) for _ in range(length - len(pwd))]
    result = list(pwd)
    for i in range(len(result) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        result[i], result[j] = result[j], result[i]
    return ''.join(result)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Request body is required'}}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    display_name = data.get('display_name', '').strip() or None

    err = validate_username(username)
    if err:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': err}}), 400

    if not email:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Email is required'}}), 400

    err = validate_password(password)
    if err:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': err}}), 400

    try:
        user = auth_service.register_user(username, email, password)
        user.display_name = display_name
        user.login_code = generate_login_code()
        db.session.commit()

        return jsonify({
            'id': user.id,
            'username': user.username,
            'display_name': user.get_display_name(),
            'tag': user.get_full_tag(),
            'email': user.email,
            'is_author': user.is_author,
            'is_admin': user.is_admin,
            'is_moderator': getattr(user, 'is_moderator', False),
            'created_at': user.created_at.isoformat()
        }), 201
    except ValueError as e:
        error_message = str(e)
        if 'already exists' in error_message:
            return jsonify({'error': {'code': 'CONFLICT', 'message': error_message}}), 409
        return jsonify({'error': {'code': 'UNPROCESSABLE_ENTITY', 'message': error_message}}), 422


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Request body is required'}}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Username and password are required'}}), 400

    user = auth_service.authenticate(username, password)
    if not user:
        return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid username or password'}}), 401

    token = auth_service.create_session(user)

    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'display_name': user.get_display_name(),
            'tag': user.get_full_tag(),
            'email': user.email,
            'is_author': user.is_author,
            'is_admin': user.is_admin,
            'is_moderator': getattr(user, 'is_moderator', False),
            'is_vip': user.is_vip,
            'mexels': user.mexels,
            'avatar_url': user.avatar_url,
            'bio': user.bio,
            'notifications_enabled': user.notifications_enabled,
            'created_at': user.created_at.isoformat()
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    auth_header = request.headers.get('Authorization')
    token = auth_header.split()[1]
    auth_service.terminate_session(token)
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    user = request.current_user
    return jsonify({
        'id': user.id,
        'username': user.username,
        'display_name': user.get_display_name(),
        'tag': user.get_full_tag(),
        'email': user.email,
        'is_author': user.is_author,
        'is_admin': user.is_admin,
        'is_moderator': getattr(user, 'is_moderator', False),
        'is_vip': user.is_vip,
        'mexels': user.mexels,
        'avatar_url': user.avatar_url,
        'bio': user.bio,
        'notifications_enabled': user.notifications_enabled,
        'created_at': user.created_at.isoformat()
    }), 200


@auth_bp.route('/me', methods=['PUT'])
@require_auth
def update_profile():
    user = request.current_user
    data = request.get_json()
    if not data:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Request body is required'}}), 400

    if 'display_name' in data:
        dn = data['display_name'].strip() if data['display_name'] else None
        if dn and len(dn) > 80:
            return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Display name max 80 characters'}}), 400
        user.display_name = dn

    if 'bio' in data:
        bio = data['bio'].strip() if data['bio'] else None
        if bio and len(bio) > 500:
            return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Bio max 500 characters'}}), 400
        user.bio = bio

    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']

    if 'notifications_enabled' in data:
        user.notifications_enabled = bool(data['notifications_enabled'])

    db.session.commit()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'display_name': user.get_display_name(),
        'tag': user.get_full_tag(),
        'email': user.email,
        'is_author': user.is_author,
        'is_admin': user.is_admin,
        'is_vip': user.is_vip,
        'mexels': user.mexels,
        'avatar_url': user.avatar_url,
        'bio': user.bio,
        'notifications_enabled': user.notifications_enabled,
        'created_at': user.created_at.isoformat()
    }), 200


@auth_bp.route('/password-strength', methods=['POST'])
def password_strength():
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Password is required'}}), 400
    pwd = data['password']
    err = validate_password(pwd)
    if err:
        return jsonify({'strength': 'invalid', 'message': err}), 200
    return jsonify({'strength': check_password_strength(pwd)}), 200


@auth_bp.route('/generate-password', methods=['GET'])
def gen_password():
    pwd = generate_password()
    return jsonify({'password': pwd, 'strength': check_password_strength(pwd)}), 200


@auth_bp.route('/vip/buy', methods=['POST'])
@require_auth
def buy_vip():
    user = request.current_user
    VIP_COST = 100
    if user.is_vip:
        return jsonify({'error': {'code': 'CONFLICT', 'message': 'Already VIP'}}), 409
    if user.mexels < VIP_COST:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': f'Not enough mexels. Need {VIP_COST}, have {user.mexels}'}}), 400
    user.mexels -= VIP_COST
    user.is_vip = True
    db.session.commit()
    return jsonify({'message': 'VIP activated!', 'mexels': user.mexels, 'is_vip': True}), 200


@auth_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'display_name': user.get_display_name(),
        'tag': user.get_full_tag(),
        'is_author': user.is_author,
        'is_vip': user.is_vip,
        'avatar_url': user.avatar_url,
        'bio': user.bio,
        'created_at': user.created_at.isoformat()
    }), 200
