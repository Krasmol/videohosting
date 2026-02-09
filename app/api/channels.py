from flask import Blueprint, request, jsonify
from app.services.channel_service import ChannelService
from app.services.video_service import VideoService
from app.api.auth import require_auth
from app.models import Channel

video_service = VideoService()

channels_bp = Blueprint('channels', __name__)

channel_service = ChannelService()


@channels_bp.route('', methods=['GET'])
def list_channels():
    try:
        channels = Channel.query.all()

        return jsonify([{
            'id': channel.id,
            'author_id': channel.author_id,
            'name': channel.name,
            'description': channel.description,
            'subscriber_count': channel.subscriber_count,
            'created_at': channel.created_at.isoformat()
        } for channel in channels]), 200

    except Exception as e:
        return jsonify({
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


@channels_bp.route('', methods=['POST'])
@require_auth
def create_channel():
    user = request.current_user
    data = request.get_json()

    if not data:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Request body is required'
            }
        }), 400

    name = data.get('name')
    if not name:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Channel name is required'
            }
        }), 400

    description = data.get('description')

    try:
        channel = channel_service.create_channel(user, name, description)
        return jsonify(channel_service.to_dict(channel)), 201

    except ValueError as e:
        error_message = str(e)

        if 'already has a channel' in error_message:
            return jsonify({
                'error': {
                    'code': 'CONFLICT',
                    'message': error_message
                }
            }), 409
        else:
            return jsonify({
                'error': {
                    'code': 'UNPROCESSABLE_ENTITY',
                    'message': error_message
                }
            }), 422


@channels_bp.route('/<int:channel_id>', methods=['GET'])
def get_channel(channel_id):
    channel = channel_service.get_channel(channel_id)

    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Channel with id {channel_id} not found'
            }
        }), 404

    return jsonify(channel_service.to_dict(channel)), 200


@channels_bp.route('/<int:channel_id>', methods=['PUT'])
@require_auth
def update_channel(channel_id):
    user = request.current_user
    data = request.get_json()

    if not data:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Request body is required'
            }
        }), 400

    channel = channel_service.get_channel(channel_id)
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Channel with id {channel_id} not found'
            }
        }), 404

    if channel.author_id != user.id:
        return jsonify({
            'error': {
                'code': 'FORBIDDEN',
                'message': 'You do not have permission to update this channel'
            }
        }), 403

    try:
        updated_channel = channel_service.update_channel(channel_id, **data)
        return jsonify(channel_service.to_dict(updated_channel)), 200

    except ValueError as e:
        return jsonify({
            'error': {
                'code': 'UNPROCESSABLE_ENTITY',
                'message': str(e)
            }
        }), 422


@channels_bp.route('/<int:channel_id>/videos', methods=['GET'])
def get_channel_videos(channel_id):
    status = request.args.get('status')

    try:
        videos = channel_service.get_channel_videos(channel_id, status)

        return jsonify({
            'channel_id': channel_id,
            'videos': [
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
                    'thumbnail_url': video_service.get_thumbnail_url(video) if hasattr(video_service, 'get_thumbnail_url') else None,
                    'created_at': video.created_at.isoformat()
                }
                for video in videos
            ]
        }), 200

    except ValueError as e:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': str(e)
            }
        }), 404
