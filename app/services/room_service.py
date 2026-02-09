from typing import Optional, List, Dict, Any
from datetime import datetime
from app import db
from app.models import Room, RoomParticipant, RoomInvitation, User, Video, Subscription


class RoomService:

    @staticmethod
    def create_room(host_id: int, video_id: int, max_participants: Optional[int] = None, name: Optional[str] = None) -> Room:
        video = Video.query.get(video_id)
        if not video:
            raise ValueError(f"Video with id {video_id} not found")

        if max_participants is None:
            subscription = Subscription.query.filter_by(user_id=host_id, channel_id=video.channel_id).first()
            if subscription:
                max_participants = None
            else:
                max_participants = 10

        room = Room(
            owner_id=host_id,
            video_id=video_id,
            name=name,
            max_participants=max_participants or 10,
            last_activity=datetime.utcnow()
        )
        db.session.add(room)
        db.session.commit()

        RoomService.join_room(room.id, host_id)
        return room

    @staticmethod
    def get_room(room_id: int) -> Room:
        room = Room.query.get(room_id)
        if not room:
            raise ValueError(f"Room with id {room_id} not found")
        return room

    @staticmethod
    def get_active_rooms() -> List[Room]:
        return Room.query.all()

    @staticmethod
    def join_room(room_id: int, user_id: int) -> RoomParticipant:
        room = Room.query.get(room_id)
        if not room:
            raise ValueError(f"Room with id {room_id} not found")

        existing = RoomParticipant.query.filter_by(room_id=room_id, user_id=user_id).first()
        if existing:
            return existing

        current_count = RoomParticipant.query.filter_by(room_id=room_id).count()
        if room.max_participants is not None and current_count >= room.max_participants:
            raise ValueError("Room is full")

        participant = RoomParticipant(room_id=room_id, user_id=user_id)
        db.session.add(participant)
        room.last_activity = datetime.utcnow()
        db.session.commit()
        return participant

    @staticmethod
    def leave_room(room_id: int, user_id: int) -> bool:
        participant = RoomParticipant.query.filter_by(room_id=room_id, user_id=user_id).first()
        if not participant:
            raise ValueError("User is not in this room")

        db.session.delete(participant)
        db.session.commit()

        room = Room.query.get(room_id)
        if room:
            remaining = RoomParticipant.query.filter_by(room_id=room_id).count()
            if remaining == 0:
                db.session.delete(room)
                db.session.commit()
        return True

    @staticmethod
    def kick_user(room_id: int, host_id: int, user_id: int) -> bool:
        room = Room.query.get(room_id)
        if not room:
            raise ValueError(f"Room with id {room_id} not found")
        if room.owner_id != host_id:
            raise PermissionError("Only the host can kick users")
        if user_id == host_id:
            raise ValueError("Host cannot kick themselves")

        participant = RoomParticipant.query.filter_by(room_id=room_id, user_id=user_id).first()
        if not participant:
            raise ValueError("User is not in this room")

        db.session.delete(participant)
        db.session.commit()
        return True

    @staticmethod
    def invite_user(room_id: int, inviter_id: int, invitee_id: int) -> RoomInvitation:
        room = Room.query.get(room_id)
        if not room:
            raise ValueError(f"Room with id {room_id} not found")

        inviter_participant = RoomParticipant.query.filter_by(room_id=room_id, user_id=inviter_id).first()
        if not inviter_participant:
            raise ValueError("You must be in the room to invite others")

        invitee = User.query.get(invitee_id)
        if not invitee:
            raise ValueError(f"User with id {invitee_id} not found")

        existing = RoomInvitation.query.filter_by(room_id=room_id, recipient_id=invitee_id).first()
        if existing:
            return existing

        invitation = RoomInvitation(room_id=room_id, sender_id=inviter_id, recipient_id=invitee_id)
        db.session.add(invitation)
        db.session.commit()
        return invitation

    @staticmethod
    def to_dict(room: Room, include_participants: bool = False) -> Dict[str, Any]:
        current_participants = RoomParticipant.query.filter_by(room_id=room.id).count()
        data = {
            'id': room.id,
            'owner_id': room.owner_id,
            'video_id': room.video_id,
            'name': room.name,
            'max_participants': room.max_participants,
            'current_participants': current_participants,
            'last_activity': room.last_activity.isoformat() if room.last_activity else None,
            'created_at': room.created_at.isoformat()
        }
        if include_participants:
            participants = RoomParticipant.query.filter_by(room_id=room.id).all()
            data['participants'] = []
            for p in participants:
                user = User.query.get(p.user_id)
                data['participants'].append({
                    'id': p.id,
                    'user_id': p.user_id,
                    'display_name': user.get_display_name() if user else f'User #{p.user_id}',
                    'tag': user.get_full_tag() if user else '',
                    'joined_at': p.joined_at.isoformat()
                })
        return data
