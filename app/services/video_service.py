import os
import uuid
import subprocess
from typing import Optional, List, Dict, Any
from werkzeug.utils import secure_filename
from flask import current_app
from app import db
from app.models import Video, Channel, User, Subscription


CATEGORIES = ['gaming', 'music', 'education', 'entertainment', 'tech', 'sports', 'news', 'blog', 'other']


class VideoService:

    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}

    @staticmethod
    def _allowed_file(filename: str) -> bool:
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in VideoService.ALLOWED_EXTENSIONS

    @staticmethod
    def _allowed_image(filename: str) -> bool:
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in VideoService.ALLOWED_IMAGE_EXTENSIONS

    @staticmethod
    def _generate_thumbnail(video_file_path: str, duration: int) -> Optional[str]:
        """Generate a thumbnail at ~2 seconds (or earlier if video is short).

        Returns absolute thumbnail path or None.
        """
        try:
            thumb_folder = current_app.config['THUMBNAIL_FOLDER']
            os.makedirs(thumb_folder, exist_ok=True)

            # Pick a timestamp that makes sense for short clips.
            ts = 2
            if duration and duration > 0:
                ts = min(2, max(1, duration // 3))

            thumb_filename = f"{uuid.uuid4().hex}.jpg"
            thumbnail_path = os.path.join(thumb_folder, thumb_filename)

            cmd = [
                'ffmpeg', '-y',
                '-ss', f'00:00:{ts:02d}',
                '-i', video_file_path,
                '-frames:v', '1',
                '-q:v', '2',
                thumbnail_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
                return thumbnail_path
        except Exception:
            return None
        return None

    @staticmethod
    def upload_video(channel: Channel, file, metadata: dict, thumbnail_file=None) -> Video:
        title = metadata.get('title', '').strip()
        if not title:
            raise ValueError("Video title is required")
        if len(title) > 100:
            raise ValueError("Video title must be 100 characters or less")

        description = metadata.get('description', '').strip() if metadata.get('description') else None
        if description and len(description) > 2000:
            raise ValueError("Video description must be 2000 characters or less")

        duration = metadata.get('duration')
        if duration is None:
            raise ValueError("Video duration is required")
        try:
            duration = int(duration)
            if duration <= 0:
                raise ValueError("Video duration must be positive")
        except (TypeError, ValueError):
            raise ValueError("Video duration must be a positive integer")

        access_level = metadata.get('access_level', 'public')
        if access_level not in ['public', 'subscriber', 'sponsor']:
            raise ValueError("Access level must be 'public', 'subscriber', or 'sponsor'")

        category = metadata.get('category', 'other').strip().lower()
        if category not in CATEGORIES:
            category = 'other'

        tags = metadata.get('tags', '').strip() if metadata.get('tags') else None
        if tags and len(tags) > 500:
            tags = tags[:500]

        has_ads = metadata.get('has_ads', True)
        if not isinstance(has_ads, bool):
            has_ads = str(has_ads).lower() in ['true', '1', 'yes']

        if not file or not file.filename:
            raise ValueError("Video file is required")
        if not VideoService._allowed_file(file.filename):
            raise ValueError(f"File type not allowed. Allowed types: {', '.join(VideoService.ALLOWED_EXTENSIONS)}")

        file_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, unique_filename)

        try:
            file.save(file_path)
        except Exception as e:
            raise ValueError(f"Failed to save video file: {str(e)}")

        thumbnail_path = None
        if thumbnail_file and thumbnail_file.filename:
            if VideoService._allowed_image(thumbnail_file.filename):
                thumb_ext = thumbnail_file.filename.rsplit('.', 1)[1].lower()
                thumb_filename = f"{uuid.uuid4().hex}.{thumb_ext}"
                thumb_folder = current_app.config['THUMBNAIL_FOLDER']
                thumbnail_path = os.path.join(thumb_folder, thumb_filename)
                try:
                    thumbnail_file.save(thumbnail_path)
                except Exception:
                    thumbnail_path = None

        # Auto-thumbnail if user didn't provide one.
        if thumbnail_path is None:
            thumbnail_path = VideoService._generate_thumbnail(file_path, duration)

        video = Video(
            channel_id=channel.id,
            title=title,
            description=description,
            file_path=file_path,
            thumbnail_path=thumbnail_path,
            duration=duration,
            category=category,
            all_categories=bool(metadata.get('all_categories', False)),
            tags=tags,
            access_level=access_level,
            has_ads=has_ads,
            status='ready'
        )

        db.session.add(video)
        db.session.commit()
        return video

    @staticmethod
    def get_video(video_id: int) -> Optional[Video]:
        return Video.query.get(video_id)

    @staticmethod
    def increment_views(video_id: int, user=None):
        from app import redis_client
        viewer_key = f"view:{video_id}:{user.id if user else 'anon'}"
        if redis_client:
            already = redis_client.get(viewer_key)
            if already:
                return
            redis_client.setex(viewer_key, 1800, "1")
        video = Video.query.get(video_id)
        if video:
            video.views_count = (video.views_count or 0) + 1
            db.session.commit()

    @staticmethod
    def delete_video(video_id: int) -> bool:
        video = Video.query.get(video_id)
        if not video:
            raise ValueError(f"Video with id {video_id} not found")
        if os.path.exists(video.file_path):
            try:
                os.remove(video.file_path)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete video file {video.file_path}: {str(e)}")
        if video.thumbnail_path and os.path.exists(video.thumbnail_path):
            try:
                os.remove(video.thumbnail_path)
            except Exception:
                pass
        db.session.delete(video)
        db.session.commit()
        return True

    @staticmethod
    def check_access(video: Video, user: Optional[User]) -> bool:
        if video.access_level == 'public':
            return True
        if not user:
            return False
        if video.channel.author_id == user.id:
            return True
        subscription = Subscription.query.filter_by(user_id=user.id, channel_id=video.channel_id).first()
        if not subscription:
            return False
        if video.access_level == 'subscriber':
            return True
        if video.access_level == 'sponsor':
            return subscription.is_sponsor
        return False

    @staticmethod
    def should_show_ads(video: Video, user: Optional[User]) -> bool:
        if not video.has_ads:
            return False
        if video.access_level in ['subscriber', 'sponsor']:
            return False
        if not user:
            return True
        if video.channel.author_id == user.id:
            return False
        subscription = Subscription.query.filter_by(user_id=user.id, channel_id=video.channel_id).first()
        if subscription and subscription.is_sponsor:
            return False
        return True

    @staticmethod
    def get_access_info(video: Video, user: Optional[User]) -> Dict[str, Any]:
        has_access = VideoService.check_access(video, user)
        show_ads = VideoService.should_show_ads(video, user) if has_access else False
        is_sponsor = False
        is_subscriber = False
        reason = None
        if user:
            subscription = Subscription.query.filter_by(user_id=user.id, channel_id=video.channel_id).first()
            if subscription:
                is_subscriber = True
                is_sponsor = subscription.is_sponsor
        if not has_access:
            if video.access_level == 'subscriber':
                reason = 'Это видео доступно только подписчикам канала'
            elif video.access_level == 'sponsor':
                reason = 'Это видео доступно только спонсорам канала'
            elif not user:
                reason = 'Войдите, чтобы посмотреть это видео'
        return {
            'has_access': has_access,
            'show_ads': show_ads,
            'access_level': video.access_level,
            'reason': reason,
            'is_sponsor': is_sponsor,
            'is_subscriber': is_subscriber
        }

    @staticmethod
    def get_stream_url(video: Video) -> str:
        if video.status != 'ready':
            raise ValueError(f"Video is not ready for streaming (status: {video.status})")
        filename = os.path.basename(video.file_path)
        return f"/videos/{filename}"

    @staticmethod
    def get_thumbnail_url(video: Video) -> Optional[str]:
        # Happy path
        if video.thumbnail_path and os.path.exists(video.thumbnail_path):
            filename = os.path.basename(video.thumbnail_path)
            return f"/thumbnails/{filename}"

        # Lazy auto-generation for older uploads that don't have a thumbnail yet.
        # This keeps the UI from showing "нет превью" when ffmpeg is available.
        try:
            if (not video.thumbnail_path) and video.file_path and os.path.exists(video.file_path):
                thumb = VideoService._generate_thumbnail(video.file_path, int(video.duration or 0))
                if thumb:
                    video.thumbnail_path = thumb
                    db.session.commit()
                    filename = os.path.basename(video.thumbnail_path)
                    return f"/thumbnails/{filename}"
        except Exception:
            # If generation fails (no ffmpeg/codec issues), just return None.
            pass
        return None

    @staticmethod
    def get_videos_by_channel(channel_id: int, status: str = None) -> List[Video]:
        query = Video.query.filter_by(channel_id=channel_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(Video.created_at.desc()).all()

    @staticmethod
    def to_dict(video: Video, include_stream_url: bool = False) -> Dict[str, Any]:
        data = {
            'id': video.id,
            'channel_id': video.channel_id,
            'title': video.title,
            'description': video.description,
            'duration': video.duration,
            'category': video.category or 'other',
            'all_categories': bool(getattr(video, 'all_categories', False)),
            'tags': video.tags,
            'access_level': video.access_level,
            'has_ads': video.has_ads,
            'status': video.status,
            'views_count': video.views_count or 0,
            'likes_count': video.likes_count,
            'dislikes_count': video.dislikes_count,
            'thumbnail_url': VideoService.get_thumbnail_url(video),
            'created_at': video.created_at.isoformat()
        }
        if include_stream_url and video.status == 'ready':
            try:
                data['stream_url'] = VideoService.get_stream_url(video)
            except ValueError:
                pass
        return data
