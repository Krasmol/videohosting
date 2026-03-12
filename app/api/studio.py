from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.api.auth import require_auth
from app.models import Channel, Video, VideoView, DailyVideoStats, Subscription, VideoComment
from app.services.video_service import VideoService
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func
import os
from PIL import Image

studio_bp = Blueprint('studio', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@studio_bp.route('/dashboard', methods=['GET'])
@require_auth
def get_dashboard():
    """Получить общую статистику канала"""
    user = request.current_user

    # Проверка наличия канала
    channel = Channel.query.filter_by(author_id=user.id).first()
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Channel not found. Create a channel first.'
            }
        }), 404

    # Получить все видео канала
    videos = Video.query.filter_by(channel_id=channel.id).all()

    # Общая статистика
    total_videos = len(videos)
    total_views = sum(v.views_count for v in videos)
    total_likes = sum(v.likes_count for v in videos)
    total_subscribers = channel.subscriber_count

    # Топ-3 видео по просмотрам
    top_videos = sorted(videos, key=lambda v: v.views_count or 0, reverse=True)[:3]

    # Упрощённый график: показываем общие просмотры за сегодня
    # Для учебного проекта без сложной аналитики
    today = datetime.utcnow().date()
    views_chart = []

    # Создать список за 30 дней с общими просмотрами на сегодня
    for i in range(30):
        date = (today - timedelta(days=29-i))
        # Показываем просмотры только на сегодняшний день
        views = total_views if date == today else 0
        views_chart.append({
            'date': date.isoformat(),
            'views': views
        })

    return jsonify({
        'channel': {
            'id': channel.id,
            'name': channel.name,
            'subscriber_count': total_subscribers
        },
        'stats': {
            'total_videos': total_videos,
            'total_views': total_views,
            'total_likes': total_likes,
            'total_subscribers': total_subscribers
        },
        'top_videos': [{
            'id': v.id,
            'title': v.title,
            'views_count': v.views_count,
            'likes_count': v.likes_count,
            'thumbnail_url': VideoService.get_thumbnail_url(v)
        } for v in top_videos],
        'views_chart': views_chart
    }), 200


@studio_bp.route('/videos', methods=['GET'])
@require_auth
def get_studio_videos():
    """Получить список всех видео с расширенной информацией"""
    user = request.current_user

    channel = Channel.query.filter_by(author_id=user.id).first()
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Channel not found'
            }
        }), 404

    videos = Video.query.filter_by(channel_id=channel.id).order_by(Video.created_at.desc()).all()

    from app.services.video_service import VideoService

    return jsonify({
        'videos': [{
            'id': v.id,
            'title': v.title,
            'description': v.description,
            'status': v.status,
            'views_count': v.views_count,
            'likes_count': v.likes_count,
            'dislikes_count': v.dislikes_count,
            'comments_count': VideoComment.query.filter_by(video_id=v.id, deleted_at=None).count(),
            'duration': v.duration,
            'category': v.category,
            'access_level': v.access_level,
            'thumbnail_url': VideoService.get_thumbnail_url(v),
            'created_at': v.created_at.isoformat()
        } for v in videos]
    }), 200


@studio_bp.route('/videos/<int:video_id>', methods=['PUT'])
@require_auth
def update_video_metadata(video_id):
    """Редактировать метаданные видео"""
    user = request.current_user
    data = request.get_json()

    if not data:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Request body is required'
            }
        }), 400

    video = Video.query.get(video_id)
    if not video:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Video not found'
            }
        }), 404

    # Проверка прав
    channel = Channel.query.get(video.channel_id)
    if not channel or channel.author_id != user.id:
        return jsonify({
            'error': {
                'code': 'FORBIDDEN',
                'message': 'You do not have permission to edit this video'
            }
        }), 403

    # Обновление полей
    if 'title' in data:
        video.title = data['title'][:100]
    if 'description' in data:
        video.description = data['description'][:2000]
    if 'category' in data:
        video.category = data['category']
    if 'tags' in data:
        video.tags = data['tags'][:500]
    if 'access_level' in data:
        video.access_level = data['access_level']

    db.session.commit()

    return jsonify({
        'message': 'Video updated successfully',
        'video': {
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'category': video.category,
            'tags': video.tags,
            'access_level': video.access_level,
            'thumbnail_url': VideoService.get_thumbnail_url(video)
        }
    }), 200


@studio_bp.route('/videos/<int:video_id>/thumbnail', methods=['POST'])
@require_auth
def upload_custom_thumbnail(video_id):
    """Загрузить кастомное превью для видео"""
    user = request.current_user

    video = Video.query.get(video_id)
    if not video:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Video not found'
            }
        }), 404

    # Проверка прав
    channel = Channel.query.get(video.channel_id)
    if not channel or channel.author_id != user.id:
        return jsonify({
            'error': {
                'code': 'FORBIDDEN',
                'message': 'You do not have permission to edit this video'
            }
        }), 403

    if 'thumbnail' not in request.files:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'No thumbnail file provided'
            }
        }), 400

    file = request.files['thumbnail']
    if file.filename == '':
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'No file selected'
            }
        }), 400

    if not allowed_image_file(file.filename):
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Invalid file type. Allowed: png, jpg, jpeg, webp'
            }
        }), 400

    try:
        # Удалить старое превью если есть
        if video.custom_thumbnail_path and os.path.exists(video.custom_thumbnail_path):
            try:
                os.remove(video.custom_thumbnail_path)
            except:
                pass

        # Сохранить новое превью
        filename = secure_filename(f"video_{video.id}_custom_{int(datetime.utcnow().timestamp())}.jpg")
        thumbnail_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], filename)

        # Открыть и оптимизировать изображение
        img = Image.open(file)

        # Конвертировать в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background

        # Изменить размер до 1280x720 (16:9)
        img.thumbnail((1280, 720), Image.Resampling.LANCZOS)

        # Сохранить с оптимизацией
        img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)

        video.custom_thumbnail_path = thumbnail_path
        db.session.commit()

        return jsonify({
            'message': 'Thumbnail uploaded successfully',
            'thumbnail_url': VideoService.get_thumbnail_url(video)
        }), 200

    except Exception as e:
        return jsonify({
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': f'Failed to upload thumbnail: {str(e)}'
            }
        }), 500


@studio_bp.route('/videos/<int:video_id>/thumbnail', methods=['DELETE'])
@require_auth
def delete_custom_thumbnail(video_id):
    """Удалить кастомное превью и вернуться к автоматическому"""
    user = request.current_user

    video = Video.query.get(video_id)
    if not video:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Video not found'
            }
        }), 404

    # Проверка прав
    channel = Channel.query.get(video.channel_id)
    if not channel or channel.author_id != user.id:
        return jsonify({
            'error': {
                'code': 'FORBIDDEN',
                'message': 'You do not have permission to edit this video'
            }
        }), 403

    if video.custom_thumbnail_path:
        if os.path.exists(video.custom_thumbnail_path):
            try:
                os.remove(video.custom_thumbnail_path)
            except:
                pass
        video.custom_thumbnail_path = None
        db.session.commit()

    return jsonify({
        'message': 'Custom thumbnail deleted',
        'thumbnail_url': VideoService.get_thumbnail_url(video)
    }), 200


@studio_bp.route('/analytics/views', methods=['GET'])
@require_auth
def get_analytics_views():
    """Получить аналитику просмотров по дням"""
    user = request.current_user
    days = request.args.get('days', 30, type=int)
    days = min(days, 365)  # Максимум год

    channel = Channel.query.filter_by(author_id=user.id).first()
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Channel not found'
            }
        }), 404

    start_date = datetime.utcnow().date() - timedelta(days=days-1)

    daily_stats = db.session.query(
        DailyVideoStats.date,
        func.sum(DailyVideoStats.views).label('views'),
        func.sum(DailyVideoStats.watch_time).label('watch_time')
    ).join(Video).filter(
        Video.channel_id == channel.id,
        DailyVideoStats.date >= start_date
    ).group_by(DailyVideoStats.date).order_by(DailyVideoStats.date).all()

    views_data = []
    for i in range(days):
        date = (datetime.utcnow().date() - timedelta(days=days-1-i))
        stat = next((s for s in daily_stats if s.date == date), None)
        views_data.append({
            'date': date.isoformat(),
            'views': stat.views if stat else 0,
            'watch_time': stat.watch_time if stat else 0
        })

    return jsonify({'views_data': views_data}), 200


@studio_bp.route('/analytics/traffic', methods=['GET'])
@require_auth
def get_analytics_traffic():
    """Получить источники трафика"""
    user = request.current_user

    channel = Channel.query.filter_by(author_id=user.id).first()
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Channel not found'
            }
        }), 404

    # Получить источники за последние 30 дней
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    traffic_sources = db.session.query(
        VideoView.source,
        func.count(VideoView.id).label('count')
    ).join(Video).filter(
        Video.channel_id == channel.id,
        VideoView.viewed_at >= thirty_days_ago
    ).group_by(VideoView.source).all()

    source_labels = {
        'direct': 'Прямые переходы',
        'search': 'Поиск',
        'recommended': 'Рекомендации',
        'channel': 'Страница канала'
    }

    return jsonify({
        'traffic_sources': [{
            'source': source_labels.get(s.source, s.source),
            'count': s.count
        } for s in traffic_sources]
    }), 200


@studio_bp.route('/analytics/engagement', methods=['GET'])
@require_auth
def get_analytics_engagement():
    """Получить метрики вовлечённости"""
    user = request.current_user

    channel = Channel.query.filter_by(author_id=user.id).first()
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Channel not found'
            }
        }), 404

    videos = Video.query.filter_by(channel_id=channel.id).all()

    total_views = sum(v.views_count for v in videos)
    total_likes = sum(v.likes_count for v in videos)
    total_dislikes = sum(v.dislikes_count for v in videos)
    total_comments = sum(VideoComment.query.filter_by(video_id=v.id, deleted_at=None).count() for v in videos)

    # Средний engagement rate
    engagement_rate = 0
    if total_views > 0:
        engagement_rate = ((total_likes + total_comments) / total_views) * 100

    return jsonify({
        'engagement': {
            'total_likes': total_likes,
            'total_dislikes': total_dislikes,
            'total_comments': total_comments,
            'engagement_rate': round(engagement_rate, 2),
            'like_ratio': round((total_likes / (total_likes + total_dislikes) * 100), 2) if (total_likes + total_dislikes) > 0 else 0
        }
    }), 200


@studio_bp.route('/monetization', methods=['GET'])
@require_auth
def get_monetization():
    """Получить данные о монетизации"""
    user = request.current_user

    channel = Channel.query.filter_by(author_id=user.id).first()
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Channel not found'
            }
        }), 404

    # Получить спонсоров
    sponsors = Subscription.query.filter_by(channel_id=channel.id, is_sponsor=True).all()

    # Заглушка для дохода от рекламы
    ad_revenue = 0  # TODO: реализовать систему монетизации

    return jsonify({
        'monetization': {
            'sponsors_count': len(sponsors),
            'ad_revenue': ad_revenue,
            'total_revenue': ad_revenue
        }
    }), 200
