from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from app import db
from app.services.room_service import RoomService
from app.models import Room, RoomParticipant, User, ChatMessage
from app.api.auth import require_auth
from app.websocket.room_events import kick_user_from_room

rooms_bp = Blueprint('rooms', __name__)
room_service = RoomService()

INACTIVE_MINUTES = 30


def cleanup_inactive_rooms():
    cutoff = datetime.utcnow() - timedelta(minutes=INACTIVE_MINUTES)
    inactive = Room.query.filter(Room.last_activity < cutoff).all()
    for room in inactive:
        db.session.delete(room)
    empty = Room.query.filter(~Room.participants.any()).all()
    for room in empty:
        db.session.delete(room)
    stale_cutoff = datetime.utcnow() - timedelta(minutes=5)
    from app.websocket.room_events import active_connections
    active_user_rooms = set()
    for sid, info in active_connections.items():
        if info.get('room_id') and info.get('user_id'):
            active_user_rooms.add((info['room_id'], info['user_id']))
    all_participants = RoomParticipant.query.all()
    for p in all_participants:
        if (p.room_id, p.user_id) not in active_user_rooms:
            room = Room.query.get(p.room_id)
            if room and room.last_activity < stale_cutoff:
                db.session.delete(p)
    db.session.commit()
    empty2 = Room.query.filter(~Room.participants.any()).all()
    for room in empty2:
        db.session.delete(room)
    if empty2:
        db.session.commit()


@rooms_bp.route('', methods=['POST'])
@require_auth
def create_room():
    user = request.current_user
    data = request.get_json()
    if not data or 'video_id' not in data:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'video_id is required'}}), 400

    room_name = data.get('name', '').strip() or None
    if room_name and len(room_name) > 100:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Room name max 100 characters'}}), 400

    try:
        room = room_service.create_room(
            host_id=user.id,
            video_id=data['video_id'],
            max_participants=data.get('max_participants'),
            name=room_name
        )
        return jsonify(room_service.to_dict(room)), 201
    except ValueError as e:
        return jsonify({'error': {'code': 'UNPROCESSABLE_ENTITY', 'message': str(e)}}), 422


@rooms_bp.route('/<int:room_id>', methods=['GET'])
def get_room(room_id):
    try:
        room = room_service.get_room(room_id)
        return jsonify(room_service.to_dict(room, include_participants=True)), 200
    except ValueError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404


@rooms_bp.route('', methods=['GET'])
def list_rooms():
    cleanup_inactive_rooms()
    rooms = room_service.get_active_rooms()
    return jsonify([room_service.to_dict(room) for room in rooms]), 200


@rooms_bp.route('/<int:room_id>', methods=['DELETE'])
@require_auth
def delete_room(room_id):
    user = request.current_user
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Room not found'}}), 404
    if room.owner_id != user.id and not user.is_admin:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Only owner or admin can delete room'}}), 403
    db.session.delete(room)
    db.session.commit()
    return jsonify({'message': 'Room deleted'}), 200


@rooms_bp.route('/<int:room_id>/join', methods=['POST'])
@require_auth
def join_room(room_id):
    user = request.current_user
    try:
        participant = room_service.join_room(room_id, user.id)
        room = Room.query.get(room_id)
        if room:
            room.last_activity = datetime.utcnow()
            db.session.commit()
        return jsonify({'message': 'Joined room successfully', 'participant_id': participant.id}), 200
    except ValueError as e:
        error_msg = str(e)
        if 'full' in error_msg.lower():
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': error_msg}}), 403
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': error_msg}}), 404


@rooms_bp.route('/<int:room_id>/leave', methods=['POST'])
@require_auth
def leave_room(room_id):
    user = request.current_user
    try:
        room_service.leave_room(room_id, user.id)
        return jsonify({'message': 'Left room successfully'}), 200
    except ValueError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404


@rooms_bp.route('/<int:room_id>/leave', methods=['GET'])
def leave_room_beacon(room_id):
    token = request.args.get('token')
    if not token:
        return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Token required'}}), 401
    from app.services.auth_service import AuthService
    auth_service = AuthService()
    user = auth_service.validate_session(token)
    if not user:
        return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid token'}}), 401
    try:
        room_service.leave_room(room_id, user.id)
        return jsonify({'message': 'Left room successfully'}), 200
    except ValueError:
        return jsonify({'message': 'OK'}), 200


@rooms_bp.route('/<int:room_id>/beacon-leave', methods=['POST'])
def beacon_leave(room_id):
    token = request.args.get('token')
    if not token:
        return '', 204
    from app.services.auth_service import AuthService
    auth_service = AuthService()
    user = auth_service.validate_session(token)
    if not user:
        return '', 204
    try:
        room_service.leave_room(room_id, user.id)
    except ValueError:
        pass
    return '', 204


@rooms_bp.route('/<int:room_id>/kick/<int:user_id>', methods=['POST'])
@require_auth
def kick_user(room_id, user_id):
    host = request.current_user
    try:
        room_service.kick_user(room_id, host.id, user_id)
        # HTTP kick удаляет участника из БД, но сокет мог остаться подключенным.
        # Принудительно выкидываем из Socket.IO комнаты и уведомляем клиента.
        kick_user_from_room(room_id, user_id, reason='kicked_by_host')
        return jsonify({'message': 'User kicked successfully'}), 200
    except PermissionError as e:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': str(e)}}), 403
    except ValueError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404


@rooms_bp.route('/<int:room_id>/invite', methods=['POST'])
@require_auth
def invite_user(room_id):
    user = request.current_user
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'user_id is required'}}), 400
    try:
        invitation = room_service.invite_user(room_id, user.id, data['user_id'])
        return jsonify({
            'id': invitation.id,
            'room_id': invitation.room_id,
            'inviter_id': invitation.sender_id,
            'invitee_id': invitation.recipient_id,
            'created_at': invitation.created_at.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({'error': {'code': 'UNPROCESSABLE_ENTITY', 'message': str(e)}}), 422


@rooms_bp.route('/<int:room_id>/chat', methods=['POST'])
@require_auth
def send_chat_message(room_id):
    user = request.current_user
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Room not found'}}), 404

    participant = RoomParticipant.query.filter_by(room_id=room_id, user_id=user.id).first()
    if not participant:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'You are not in this room'}}), 403

    data = request.get_json()
    if not data or not data.get('message', '').strip():
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Message is required'}}), 400

    message_text = data['message'].strip()
    if len(message_text) > 500:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Message too long (max 500)'}}), 400

    msg = ChatMessage(room_id=room_id, user_id=user.id, content=message_text)
    db.session.add(msg)
    participant.last_message_at = datetime.utcnow()
    room.last_activity = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'id': msg.id,
        'user_id': user.id,
        'display_name': user.get_display_name(),
        'message': msg.content,
        'timestamp': msg.timestamp.isoformat()
    }), 201


@rooms_bp.route('/<int:room_id>/chat', methods=['GET'])
def get_chat_messages(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Room not found'}}), 404

    after_id = request.args.get('after', 0, type=int)
    query = ChatMessage.query.filter_by(room_id=room_id)
    if after_id:
        query = query.filter(ChatMessage.id > after_id)
    messages = query.order_by(ChatMessage.id.asc()).limit(100).all()

    result = []
    for m in messages:
        u = User.query.get(m.user_id)
        result.append({
            'id': m.id,
            'user_id': m.user_id,
            'display_name': u.get_display_name() if u else f'User #{m.user_id}',
            'message': m.content,
            'timestamp': m.timestamp.isoformat()
        })

    return jsonify(result), 200
