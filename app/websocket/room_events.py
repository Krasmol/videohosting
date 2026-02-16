from flask import request
from flask_socketio import emit, join_room, leave_room, rooms
from datetime import datetime, timedelta
from app import socketio, db
from app.models import Room, RoomParticipant, ChatMessage, User
from app.services.auth_service import AuthService

active_connections = {}

message_cooldowns = {}


def kick_user_from_room(room_id: int, user_id: int, reason: str = "kicked"):
    """Принудительно выкинуть пользователя из Socket.IO комнаты и уведомить клиента.

    Это доп. слой к HTTP-kick: даже если клиент всё ещё подключен к сокету,
    он (1) получит событие 'kicked', (2) будет удалён из socket-room,
    а также мы почистим active_connections.
    """
    if not room_id or not user_id:
        return
    room_name = str(room_id)
    to_remove = []
    for sid, info in active_connections.items():
        if info.get('room_id') == room_id and info.get('user_id') == user_id:
            try:
                socketio.emit('kicked', {
                    'room_id': room_id,
                    'user_id': user_id,
                    'reason': reason,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=sid)
                # Убираем из socket-room (чтобы не получал broadcast сообщений)
                socketio.server.leave_room(sid, room_name)
            except Exception:
                # Не ломаем сервер из-за неудачного leave_room
                pass
            to_remove.append(sid)
    for sid in to_remove:
        active_connections.pop(sid, None)


def delete_room_if_empty(room_id: int):
    if not room_id:
        return
    remaining = RoomParticipant.query.filter_by(room_id=room_id).count()
    if remaining == 0:
        room = Room.query.get(room_id)
        if room:
            db.session.delete(room)
            db.session.commit()


def get_current_user():
    sid = request.sid
    if sid in active_connections:
        user_id = active_connections[sid]['user_id']
        return User.query.get(user_id)
    return None


@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f'Client disconnected: {sid}')

    if sid in active_connections:
        conn_info = active_connections[sid]
        room_id = conn_info.get('room_id')
        user_id = conn_info.get('user_id')

        if room_id:
            leave_room(str(room_id))

            participant = RoomParticipant.query.filter_by(
                room_id=room_id,
                user_id=user_id
            ).first()

            if participant:
                db.session.delete(participant)
                db.session.commit()

            delete_room_if_empty(room_id)

            emit('user_left', {
                'user_id': user_id,
                'username': conn_info.get('username'),
                'display_name': conn_info.get('display_name', conn_info.get('username')),
                'timestamp': datetime.utcnow().isoformat()
            }, room=str(room_id), skip_sid=sid)

        del active_connections[sid]


@socketio.on('join_room')
def handle_join_room(data):
    try:
        room_id = data.get('room_id')
        token = data.get('token')

        if not room_id or not token:
            emit('error', {'message': 'room_id and token are required'})
            return

        auth_service = AuthService()
        user = auth_service.validate_session(token)

        if not user:
            emit('error', {'message': 'Invalid authentication token'})
            return

        room = Room.query.get(room_id)
        if not room:
            emit('error', {'message': f'Room {room_id} not found'})
            return

        if not room.is_active:
            emit('error', {'message': 'Room is not active'})
            return

        current_participants = len(room.participants)
        if room.max_participants and current_participants >= room.max_participants:
            emit('error', {'message': 'Room is full'})
            return

        existing = RoomParticipant.query.filter_by(
            room_id=room_id,
            user_id=user.id
        ).first()

        if not existing:
            participant = RoomParticipant(
                room_id=room_id,
                user_id=user.id
            )
            db.session.add(participant)
            db.session.commit()

        join_room(str(room_id))

        room.last_activity = datetime.utcnow()
        db.session.commit()

        active_connections[request.sid] = {
            'user_id': user.id,
            'username': user.username,
            'display_name': user.get_display_name(),
            'room_id': room_id
        }

        emit('room_state', {
            'room_id': room_id,
            'video_id': room.video_id,
            'current_position': room.current_position,
            'is_playing': room.is_playing,
            'owner_id': room.owner_id,
            'participants': [
                {
                    'user_id': p.user_id,
                    'joined_at': p.joined_at.isoformat()
                }
                for p in room.participants
            ]
        })

        emit('user_joined', {
            'user_id': user.id,
            'username': user.username,
            'display_name': user.get_display_name(),
            'timestamp': datetime.utcnow().isoformat()
        }, room=str(room_id), skip_sid=request.sid)

        print(f'User {user.username} joined room {room_id}')

    except Exception as e:
        print(f'Error in join_room: {str(e)}')
        emit('error', {'message': f'Failed to join room: {str(e)}'})


@socketio.on('leave_room_event')
def handle_leave_room(data):
    try:
        room_id = data.get('room_id')
        sid = request.sid

        if sid not in active_connections:
            return

        conn_info = active_connections[sid]
        user_id = conn_info['user_id']
        username = conn_info['username']

        leave_room(str(room_id))

        participant = RoomParticipant.query.filter_by(
            room_id=room_id,
            user_id=user_id
        ).first()

        if participant:
            db.session.delete(participant)
            db.session.commit()

        delete_room_if_empty(room_id)

        active_connections[sid]['room_id'] = None

        emit('user_left', {
            'user_id': user_id,
            'username': username,
            'display_name': conn_info.get('display_name', username),
            'timestamp': datetime.utcnow().isoformat()
        }, room=str(room_id))

        print(f'User {username} left room {room_id}')

    except Exception as e:
        print(f'Error in leave_room: {str(e)}')
        emit('error', {'message': f'Failed to leave room: {str(e)}'})


@socketio.on('play')
def handle_play(data):
    try:
        room_id = data.get('room_id')
        position = data.get('position', 0)

        user = get_current_user()
        if not user:
            emit('error', {'message': 'Not authenticated'})
            return

        room = Room.query.get(room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        # Валидация: пользователь должен быть участником комнаты.
        # (После kick участник удаляется из БД, но сокет мог остаться подключенным.)
        participant = RoomParticipant.query.filter_by(
            room_id=room_id,
            user_id=user.id
        ).first()
        if not participant:
            emit('error', {'message': 'You are not a participant of this room'})
            kick_user_from_room(room_id, user.id, reason='not_participant')
            return

        if room.owner_id != user.id:
            emit('error', {'message': 'Only room owner can control playback'})
            return

        room.is_playing = True
        room.current_position = int(position)
        db.session.commit()

        emit('play_event', {
            'position': position,
            'timestamp': datetime.utcnow().isoformat()
        }, room=str(room_id), include_self=False)

    except Exception as e:
        print(f'Error in play: {str(e)}')
        emit('error', {'message': f'Failed to play: {str(e)}'})


@socketio.on('pause')
def handle_pause(data):
    try:
        room_id = data.get('room_id')
        position = data.get('position', 0)

        user = get_current_user()
        if not user:
            emit('error', {'message': 'Not authenticated'})
            return

        room = Room.query.get(room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        if room.owner_id != user.id:
            emit('error', {'message': 'Only room owner can control playback'})
            return

        room.is_playing = False
        room.current_position = int(position)
        db.session.commit()

        emit('pause_event', {
            'position': position,
            'timestamp': datetime.utcnow().isoformat()
        }, room=str(room_id), include_self=False)

    except Exception as e:
        print(f'Error in pause: {str(e)}')
        emit('error', {'message': f'Failed to pause: {str(e)}'})


@socketio.on('seek')
def handle_seek(data):
    try:
        room_id = data.get('room_id')
        position = data.get('position', 0)

        user = get_current_user()
        if not user:
            emit('error', {'message': 'Not authenticated'})
            return

        room = Room.query.get(room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        if room.owner_id != user.id:
            emit('error', {'message': 'Only room owner can control playback'})
            return

        room.current_position = int(position)
        db.session.commit()

        emit('seek_event', {
            'position': position,
            'timestamp': datetime.utcnow().isoformat()
        }, room=str(room_id), include_self=False)

    except Exception as e:
        print(f'Error in seek: {str(e)}')
        emit('error', {'message': f'Failed to seek: {str(e)}'})


@socketio.on('chat_message')
def handle_chat_message(data):
    try:
        room_id = data.get('room_id')
        message = data.get('message', '').strip()

        user = get_current_user()
        if not user:
            emit('error', {'message': 'Not authenticated'})
            return

        room = Room.query.get(room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        # ✅ ВАЖНО: пользователь должен быть участником комнаты
        participant = RoomParticipant.query.filter_by(
            room_id=room_id,
            user_id=user.id
        ).first()
        if not participant:
            emit('error', {'message': 'You are not a participant of this room'})
            kick_user_from_room(room_id, user.id, reason='not_participant')
            return

        if not message:
            emit('error', {'message': 'Message cannot be empty'})
            return

        if len(message) > 500:
            emit('error', {'message': 'Message too long (max 500 characters)'})
            return

        if room.message_delay > 0:
            if user.id not in message_cooldowns:
                message_cooldowns[user.id] = {}

            if room_id in message_cooldowns[user.id]:
                last_message_time = message_cooldowns[user.id][room_id]
                time_since_last = (datetime.utcnow() - last_message_time).total_seconds()

                if time_since_last < room.message_delay:
                    remaining = room.message_delay - time_since_last
                    emit('error', {
                        'message': f'Please wait {int(remaining)} seconds before sending another message'
                    })
                    return

        chat_message = ChatMessage(
            room_id=room_id,
            user_id=user.id,
            content=message
        )
        db.session.add(chat_message)

        participant.last_message_at = datetime.utcnow()

        db.session.commit()

        if user.id not in message_cooldowns:
            message_cooldowns[user.id] = {}
        message_cooldowns[user.id][room_id] = datetime.utcnow()

        room.last_activity = datetime.utcnow()
        db.session.commit()

        emit('chat_message_event', {
            'message_id': chat_message.id,
            'user_id': user.id,
            'username': user.username,
            'display_name': user.get_display_name(),
            'message': message,
            'timestamp': chat_message.timestamp.isoformat()
        }, room=str(room_id))

    except Exception as e:
        print(f'Error in chat_message: {str(e)}')
        emit('error', {'message': f'Failed to send message: {str(e)}'})


@socketio.on('sync_request')
def handle_sync_request(data):
    try:
        room_id = data.get('room_id')

        room = Room.query.get(room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        emit('state_sync', {
            'position': room.current_position,
            'is_playing': room.is_playing,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f'Error in sync_request: {str(e)}')
        emit('error', {'message': f'Failed to sync: {str(e)}'})
