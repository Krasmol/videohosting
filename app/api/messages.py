from flask import Blueprint, request, jsonify
from app import db
from app.models import DirectMessage, User, Notification
from app.api.auth import require_auth

messages_bp = Blueprint('messages', __name__)


@messages_bp.route('', methods=['POST'])
@require_auth
def send_message():
    user = request.current_user
    data = request.get_json()
    if not data or 'recipient_id' not in data or 'content' not in data:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'recipient_id and content required'}}), 400

    recipient = User.query.get(data['recipient_id'])
    if not recipient:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Recipient not found'}}), 404

    if recipient.id == user.id:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Cannot message yourself'}}), 400

    content = data['content'].strip()
    if not content or len(content) > 2000:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Message must be 1-2000 characters'}}), 400

    msg = DirectMessage(sender_id=user.id, recipient_id=recipient.id, content=content)
    db.session.add(msg)

    if recipient.notifications_enabled:
        notif = Notification(
            user_id=recipient.id,
            type='direct_message',
            content=f'New message from {user.get_display_name()}'
        )
        db.session.add(notif)

    db.session.commit()

    return jsonify({
        'id': msg.id,
        'sender_id': msg.sender_id,
        'recipient_id': msg.recipient_id,
        'content': msg.content,
        'created_at': msg.created_at.isoformat()
    }), 201


@messages_bp.route('/conversations', methods=['GET'])
@require_auth
def get_conversations():
    user = request.current_user
    sent = db.session.query(DirectMessage.recipient_id).filter_by(sender_id=user.id).distinct()
    received = db.session.query(DirectMessage.sender_id).filter_by(recipient_id=user.id).distinct()

    partner_ids = set()
    for row in sent:
        partner_ids.add(row[0])
    for row in received:
        partner_ids.add(row[0])

    conversations = []
    for pid in partner_ids:
        partner = User.query.get(pid)
        if not partner:
            continue
        last_msg = DirectMessage.query.filter(
            db.or_(
                db.and_(DirectMessage.sender_id == user.id, DirectMessage.recipient_id == pid),
                db.and_(DirectMessage.sender_id == pid, DirectMessage.recipient_id == user.id)
            )
        ).order_by(DirectMessage.created_at.desc()).first()

        unread = DirectMessage.query.filter_by(sender_id=pid, recipient_id=user.id, is_read=False).count()

        conversations.append({
            'user_id': partner.id,
            'display_name': partner.get_display_name(),
            'tag': partner.get_full_tag(),
            'avatar_url': partner.avatar_url,
            'last_message': last_msg.content[:100] if last_msg else '',
            'last_message_at': last_msg.created_at.isoformat() if last_msg else '',
            'unread': unread
        })

    conversations.sort(key=lambda x: x['last_message_at'], reverse=True)
    return jsonify(conversations), 200


@messages_bp.route('/with/<int:partner_id>', methods=['GET'])
@require_auth
def get_messages_with(partner_id):
    user = request.current_user
    messages = DirectMessage.query.filter(
        db.or_(
            db.and_(DirectMessage.sender_id == user.id, DirectMessage.recipient_id == partner_id),
            db.and_(DirectMessage.sender_id == partner_id, DirectMessage.recipient_id == user.id)
        )
    ).order_by(DirectMessage.created_at.asc()).limit(200).all()

    DirectMessage.query.filter_by(sender_id=partner_id, recipient_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()

    return jsonify([{
        'id': m.id,
        'sender_id': m.sender_id,
        'recipient_id': m.recipient_id,
        'content': m.content,
        'is_read': m.is_read,
        'created_at': m.created_at.isoformat()
    } for m in messages]), 200
