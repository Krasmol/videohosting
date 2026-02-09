from flask import Blueprint, request, jsonify
from datetime import datetime
from app.services.video_service import VideoService, CATEGORIES
from app.services.channel_service import ChannelService
from app.api.auth import require_auth, require_moderator
from app import db
from app.models import Video, Channel, VideoComment, ModerationLog, User
import random

videos_bp = Blueprint('videos', __name__)
video_service = VideoService()
channel_service = ChannelService()


@videos_bp.route('', methods=['POST'])
@require_auth
def upload_video():
    user = request.current_user
    channel = channel_service.get_channel_by_author(user.id)
    if not channel:
        try:
            channel = channel_service.create_channel(
                author=user,
                name=f"Канал {user.username}",
                description=f"Канал пользователя {user.username}"
            )
        except ValueError as e:
            return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500

    if 'file' not in request.files:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Video file is required'}}), 400

    file = request.files['file']
    thumbnail_file = request.files.get('thumbnail')

    metadata = {
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'duration': request.form.get('duration'),
        'access_level': request.form.get('access_level', 'public'),
        'category': request.form.get('category', 'other'),
        'all_categories': request.form.get('all_categories', '').lower() in ['true', '1', 'yes', 'on'],
        'tags': request.form.get('tags', ''),
        'has_ads': request.form.get('has_ads', 'true').lower() in ['true', '1', 'yes']
    }

    try:
        video = video_service.upload_video(channel, file, metadata, thumbnail_file)
        return jsonify(video_service.to_dict(video)), 201
    except ValueError as e:
        return jsonify({'error': {'code': 'UNPROCESSABLE_ENTITY', 'message': str(e)}}), 422


@videos_bp.route('/categories', methods=['GET'])
def get_categories():
    labels = {
        'gaming': 'Игры', 'music': 'Музыка', 'education': 'Образование',
        'entertainment': 'Развлечения', 'tech': 'Технологии', 'sports': 'Спорт',
        'news': 'Новости', 'blog': 'Блог', 'other': 'Другое'
    }
    return jsonify([{'id': c, 'name': labels.get(c, c)} for c in CATEGORIES]), 200


@videos_bp.route('/<int:video_id>', methods=['GET'])
def get_video(video_id):
    video = video_service.get_video(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': f'Video with id {video_id} not found'}}), 404
    # Hide removed videos from regular users.
    if video.status == 'removed':
        user = None
        auth_header = request.headers.get('Authorization')
        if auth_header:
            from app.services.auth_service import AuthService
            auth_service = AuthService()
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                user = auth_service.validate_session(parts[1])
        if not user or not (user.is_admin or getattr(user, 'is_moderator', False) or video.channel.author_id == user.id):
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404
    return jsonify(video_service.to_dict(video)), 200


@videos_bp.route('/<int:video_id>', methods=['DELETE'])
@require_auth
def delete_video(video_id):
    user = request.current_user
    video = video_service.get_video(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': f'Video with id {video_id} not found'}}), 404
    if video.channel.author_id != user.id and not user.is_admin:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'No permission'}}), 403
    try:
        video_service.delete_video(video_id)
        return jsonify({'message': 'Video deleted successfully'}), 200
    except ValueError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404


MODERATION_REASON_CODES = {
    'spam': 'Спам/реклама',
    'adult': '18+/неподходящий контент',
    'copyright': 'Нарушение авторских прав',
    'violence': 'Насилие/шок',
    'harassment': 'Хейт/травля',
    'other': 'Другое'
}


@videos_bp.route('/<int:video_id>/moderate/remove', methods=['POST'])
@require_auth
@require_moderator
def moderate_remove_video(video_id):
    """Soft-remove a video (moderation), keeping files intact."""
    moderator = request.current_user
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404

    data = request.get_json() or {}
    reason_code = (data.get('reason_code') or '').strip().lower()
    reason_text = (data.get('reason_text') or '').strip() or None

    if reason_code not in MODERATION_REASON_CODES:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Invalid reason_code'}}), 400
    if reason_code == 'other' and not reason_text:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'reason_text is required for other'}}), 400

    video.status = 'removed'
    log = ModerationLog(
        video_id=video.id,
        moderator_id=moderator.id,
        action='remove',
        reason_code=reason_code,
        reason_text=reason_text
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'message': 'Video removed by moderator', 'video_id': video.id}), 200


@videos_bp.route('/<int:video_id>/stream', methods=['GET'])
def get_stream_url(video_id):
    video = video_service.get_video(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': f'Video with id {video_id} not found'}}), 404
    if video.status == 'removed':
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404

    user = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            user = auth_service.validate_session(parts[1])

    if not video_service.check_access(video, user):
        if not user:
            return jsonify({'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required'}}), 401
        else:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Insufficient access level'}}), 403

    video_service.increment_views(video_id, user)

    try:
        stream_url = video_service.get_stream_url(video)
        show_ads = video_service.should_show_ads(video, user)
        return jsonify({'video_id': video.id, 'stream_url': stream_url, 'has_ads': show_ads}), 200
    except ValueError as e:
        return jsonify({'error': {'code': 'UNPROCESSABLE_ENTITY', 'message': str(e)}}), 422


@videos_bp.route('/<int:video_id>/access', methods=['GET'])
def check_video_access(video_id):
    video = video_service.get_video(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': f'Video with id {video_id} not found'}}), 404

    user = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            user = auth_service.validate_session(parts[1])

    access_info = video_service.get_access_info(video, user)
    access_info['video_id'] = video.id
    return jsonify(access_info), 200


@videos_bp.route('/feed', methods=['GET'])
def get_feed():
    category = request.args.get('category')
    query = Video.query.filter_by(status='ready', access_level='public')
    if category and category != 'all':
        query = query.filter((Video.category == category) | (Video.all_categories == True))
    all_videos = query.all()

    def video_to_feed(v):
        ch = Channel.query.get(v.channel_id)
        comments_count = VideoComment.query.filter_by(video_id=v.id, deleted_at=None).count()
        return {
            'id': v.id,
            'title': v.title,
            'description': v.description,
            'duration': v.duration,
            'category': v.category or 'other',
            'tags': v.tags,
            'access_level': v.access_level,
            'views_count': v.views_count or 0,
            'likes_count': v.likes_count,
            'dislikes_count': v.dislikes_count,
            'comments_count': comments_count,
            'thumbnail_url': video_service.get_thumbnail_url(v),
            'created_at': v.created_at.isoformat(),
            'channel': {'id': ch.id, 'name': ch.name} if ch else None
        }

    new_videos = sorted(all_videos, key=lambda v: v.created_at, reverse=True)[:12]
    popular_videos = sorted(all_videos, key=lambda v: (v.views_count or 0) + v.likes_count * 3, reverse=True)[:12]

    def rec_score(v: Video) -> float:
        # Simple hybrid: popularity + engagement + freshness.
        age_hours = max(1.0, (datetime.utcnow() - v.created_at).total_seconds() / 3600.0)
        comments_count = VideoComment.query.filter_by(video_id=v.id, deleted_at=None).count()
        base = (v.views_count or 0) * 1.0 + (v.likes_count or 0) * 4.0 + comments_count * 2.0
        # Time decay: older -> lower.
        return base / (age_hours ** 0.6)

    recommended = sorted(all_videos, key=rec_score, reverse=True)[:12]

    return jsonify({
        'recommended': [video_to_feed(v) for v in recommended],
        'new': [video_to_feed(v) for v in new_videos],
        'popular': [video_to_feed(v) for v in popular_videos],
        'total': len(all_videos)
    }), 200


@videos_bp.route('/search', methods=['GET'])
def search_videos():
    q = request.args.get('q', '').strip()
    category = request.args.get('category')
    limit = min(int(request.args.get('limit', 20)), 50)

    query = Video.query.filter_by(status='ready', access_level='public')
    if q:
        query = query.filter(Video.title.ilike(f'%{q}%'))
    if category and category != 'all':
        query = query.filter((Video.category == category) | (Video.all_categories == True))

    videos = query.order_by(Video.created_at.desc()).limit(limit).all()

    results = []
    for v in videos:
        ch = Channel.query.get(v.channel_id)
        results.append({
            'id': v.id,
            'title': v.title,
            'duration': v.duration,
            'category': v.category or 'other',
            'views_count': v.views_count or 0,
            'likes_count': v.likes_count,
            'thumbnail_url': video_service.get_thumbnail_url(v),
            'created_at': v.created_at.isoformat(),
            'channel': {'id': ch.id, 'name': ch.name} if ch else None
        })

    return jsonify(results), 200


# ---------------------------
# Comments
# ---------------------------


@videos_bp.route('/<int:video_id>/comments', methods=['GET'])
def list_comments(video_id):
    video = Video.query.get(video_id)
    if not video or video.status == 'removed':
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404
    comments = VideoComment.query.filter_by(video_id=video.id, deleted_at=None).order_by(VideoComment.created_at.asc()).limit(200).all()
    out = []
    for c in comments:
        u = User.query.get(c.user_id)
        out.append({
            'id': c.id,
            'video_id': c.video_id,
            'user': {
                'id': u.id if u else c.user_id,
                'username': u.username if u else 'deleted',
                'display_name': u.get_display_name() if u else 'Удалённый пользователь'
            },
            'content': c.content,
            'created_at': c.created_at.isoformat()
        })
    return jsonify(out), 200


@videos_bp.route('/<int:video_id>/comments', methods=['POST'])
@require_auth
def add_comment(video_id):
    user = request.current_user
    video = Video.query.get(video_id)
    if not video or video.status == 'removed':
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Комментарий не может быть пустым'}}), 400
    if len(content) > 2000:
        content = content[:2000]
    comment = VideoComment(video_id=video.id, user_id=user.id, content=content)
    db.session.add(comment)
    db.session.commit()
    return jsonify({
        'id': comment.id,
        'video_id': comment.video_id,
        'user': {'id': user.id, 'username': user.username, 'display_name': user.get_display_name()},
        'content': comment.content,
        'created_at': comment.created_at.isoformat()
    }), 201


@videos_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@require_auth
def delete_comment(comment_id):
    comment = VideoComment.query.get(comment_id)
    if not comment or comment.deleted_at:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Комментарий не найден'}}), 404
    user = request.current_user
    if comment.user_id != user.id and not (user.is_admin or getattr(user, 'is_moderator', False)):
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'No permission'}}), 403
    comment.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Комментарий удалён'}), 200


@videos_bp.route('/moderation/reasons', methods=['GET'])
def moderation_reasons():
    # Reuse the same reasons as moderator remove endpoint.
    return jsonify([{'code': k, 'name': v} for k, v in MODERATION_REASON_CODES.items()]), 200
