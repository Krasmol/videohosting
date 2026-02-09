from flask import Blueprint, request, jsonify
from app import db
from app.models import Notification
from app.api.auth import require_auth

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('', methods=['GET'])
@require_auth
def get_notifications():
    user = request.current_user
    notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([{
        'id': n.id,
        'type': n.type,
        'content': n.content,
        'is_read': n.is_read,
        'created_at': n.created_at.isoformat()
    } for n in notifs]), 200


@notifications_bp.route('/unread-count', methods=['GET'])
@require_auth
def unread_count():
    user = request.current_user
    count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({'count': count}), 200


@notifications_bp.route('/<int:notif_id>/read', methods=['POST'])
@require_auth
def mark_read(notif_id):
    user = request.current_user
    notif = Notification.query.filter_by(id=notif_id, user_id=user.id).first()
    if not notif:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Notification not found'}}), 404
    notif.is_read = True
    db.session.commit()
    return jsonify({'message': 'Marked as read'}), 200


@notifications_bp.route('/read-all', methods=['POST'])
@require_auth
def mark_all_read():
    user = request.current_user
    Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'message': 'All marked as read'}), 200
