from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Video, VideoReport, Room, Channel
from app.api.auth import require_auth, require_admin

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/stats', methods=['GET'])
@require_auth
@require_admin
def get_stats():
    return jsonify({
        'users': User.query.count(),
        'videos': Video.query.count(),
        'rooms': Room.query.filter_by(is_active=True).count(),
        'channels': Channel.query.count(),
        'reports': VideoReport.query.filter_by(status='pending').count()
    }), 200


@admin_bp.route('/users', methods=['GET'])
@require_auth
@require_admin
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'display_name': u.get_display_name(),
        'tag': u.get_full_tag(),
        'email': u.email,
        'is_author': u.is_author,
        'is_admin': u.is_admin,
        'is_moderator': getattr(u, 'is_moderator', False),
        'is_vip': u.is_vip,
        'mexels': u.mexels,
        'created_at': u.created_at.isoformat()
    } for u in users]), 200


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_auth
@require_admin
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404
    data = request.get_json()
    if 'is_admin' in data:
        user.is_admin = bool(data['is_admin'])
    if 'is_moderator' in data:
        # Admin can assign moderator role.
        user.is_moderator = bool(data['is_moderator'])
    if 'is_vip' in data:
        user.is_vip = bool(data['is_vip'])
    if 'mexels' in data:
        user.mexels = int(data['mexels'])
    if 'is_author' in data:
        user.is_author = bool(data['is_author'])
    db.session.commit()
    return jsonify({'message': 'User updated'}), 200


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_auth
@require_admin
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404
    if user.is_admin:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Cannot delete admin'}}), 403
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 200


@admin_bp.route('/reports', methods=['GET'])
@require_auth
@require_admin
def list_reports():
    reports = VideoReport.query.order_by(VideoReport.created_at.desc()).all()
    return jsonify([{
        'id': r.id,
        'video_id': r.video_id,
        'user_id': r.user_id,
        'reason': r.reason,
        'status': r.status,
        'created_at': r.created_at.isoformat()
    } for r in reports]), 200


@admin_bp.route('/reports/<int:report_id>', methods=['PUT'])
@require_auth
@require_admin
def update_report(report_id):
    report = VideoReport.query.get(report_id)
    if not report:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Report not found'}}), 404
    data = request.get_json()
    if 'status' in data:
        report.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Report updated'}), 200


@admin_bp.route('/videos/<int:video_id>', methods=['DELETE'])
@require_auth
@require_admin
def admin_delete_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404
    db.session.delete(video)
    db.session.commit()
    return jsonify({'message': 'Video deleted'}), 200
