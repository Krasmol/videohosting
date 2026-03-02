from flask import Blueprint, request, jsonify, current_app
from app.api.auth import require_auth
from werkzeug.utils import secure_filename
import os
import uuid

users_bp = Blueprint('users', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@users_bp.route('/avatar', methods=['POST'])
@require_auth
def upload_avatar():
    user = request.current_user

    if 'file' not in request.files:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'File required'
            }
        }), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'No file selected'
            }
        }), 400

    if not allowed_image(file.filename):
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Invalid format. Use jpg, png, or webp'
            }
        }), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_IMAGE_SIZE:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'File too large. Max 5MB'
            }
        }), 400

    try:
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"

        # Save file
        avatar_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads/videos'), '..', 'avatars')
        avatar_folder = os.path.abspath(avatar_folder)
        os.makedirs(avatar_folder, exist_ok=True)

        filepath = os.path.join(avatar_folder, filename)
        file.save(filepath)

        # Update user avatar_url
        from app import db
        user.avatar_url = f"/avatars/{filename}"
        db.session.commit()

        return jsonify({
            'avatar_url': user.avatar_url,
            'message': 'Avatar uploaded successfully'
        }), 200

    except Exception as e:
        return jsonify({
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'Failed to upload avatar: {str(e)}'
            }
        }), 500
