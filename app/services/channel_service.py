from typing import Optional, List, Dict, Any
from app import db
from app.models import Channel, Video, User


class ChannelService:

    @staticmethod
    def create_channel(author: User, name: str, description: str = None) -> Channel:
        if not name or not name.strip():
            raise ValueError("Channel name cannot be empty")

        if author.channel:
            raise ValueError("Author already has a channel")

        if not author.is_author:
            author.is_author = True

        channel = Channel(
            author_id=author.id,
            name=name.strip(),
            description=description.strip() if description else None
        )

        db.session.add(channel)
        db.session.commit()

        return channel

    @staticmethod
    def get_channel(channel_id: int) -> Optional[Channel]:
        return Channel.query.get(channel_id)

    @staticmethod
    def get_channel_by_author(author_id: int) -> Optional[Channel]:
        return Channel.query.filter_by(author_id=author_id).first()

    @staticmethod
    def update_channel(channel_id: int, **kwargs) -> Channel:
        channel = Channel.query.get(channel_id)
        if not channel:
            raise ValueError(f"Channel with id {channel_id} not found")

        if 'name' in kwargs:
            name = kwargs['name']
            if not name or not name.strip():
                raise ValueError("Channel name cannot be empty")
            channel.name = name.strip()

        if 'description' in kwargs:
            description = kwargs['description']
            channel.description = description.strip() if description else None

        if 'banner_url' in kwargs:
            channel.banner_url = kwargs['banner_url']

        db.session.commit()

        return channel

    @staticmethod
    def get_channel_videos(channel_id: int, status: str = None) -> List[Video]:
        channel = Channel.query.get(channel_id)
        if not channel:
            raise ValueError(f"Channel with id {channel_id} not found")

        query = Video.query.filter_by(channel_id=channel_id)

        if status:
            query = query.filter_by(status=status)

        return query.order_by(Video.created_at.desc()).all()

    @staticmethod
    def delete_channel(channel_id: int) -> bool:
        channel = Channel.query.get(channel_id)
        if not channel:
            raise ValueError(f"Channel with id {channel_id} not found")

        db.session.delete(channel)
        db.session.commit()

        return True

    @staticmethod
    def to_dict(channel: Channel, include_videos: bool = False) -> Dict[str, Any]:
        data = {
            'id': channel.id,
            'author_id': channel.author_id,
            'name': channel.name,
            'description': channel.description,
            'banner_url': channel.banner_url,
            'subscriber_count': channel.subscriber_count,
            'created_at': channel.created_at.isoformat()
        }

        if include_videos:
            data['videos'] = [
                {
                    'id': video.id,
                    'title': video.title,
                    'description': video.description,
                    'duration': video.duration,
                    'category': getattr(video, 'category', 'other') or 'other',
                    'tags': getattr(video, 'tags', None),
                    'access_level': video.access_level,
                    'status': video.status,
                    'views_count': getattr(video, 'views_count', 0) or 0,
                    'likes_count': video.likes_count,
                    'dislikes_count': video.dislikes_count,
                    'created_at': video.created_at.isoformat()
                }
                for video in channel.videos
            ]

        return data
