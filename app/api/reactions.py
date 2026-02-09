from flask import Blueprint, request, jsonify
from app import db
from app.models import Video, VideoReaction, VideoReport, Notification
from app.api.auth import require_auth

reactions_bp = Blueprint('reactions', __name__)


@reactions_bp.route('/videos/<int:video_id>/react', methods=['POST'])
@require_auth
def react_to_video(video_id):
    user = request.current_user
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404

    data = request.get_json()
    reaction_type = data.get('type') if data else None
    if reaction_type not in ('like', 'dislike'):
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'type must be like or dislike'}}), 400

    existing = VideoReaction.query.filter_by(video_id=video_id, user_id=user.id).first()

    if existing:
        if existing.reaction_type == reaction_type:
            if reaction_type == 'like':
                video.likes_count = max(0, video.likes_count - 1)
            else:
                video.dislikes_count = max(0, video.dislikes_count - 1)
            db.session.delete(existing)
            db.session.commit()
            return jsonify({
                'action': 'removed',
                'likes': video.likes_count,
                'dislikes': video.dislikes_count,
                'user_reaction': None
            }), 200
        else:
            if existing.reaction_type == 'like':
                video.likes_count = max(0, video.likes_count - 1)
            else:
                video.dislikes_count = max(0, video.dislikes_count - 1)
            existing.reaction_type = reaction_type
            if reaction_type == 'like':
                video.likes_count += 1
            else:
                video.dislikes_count += 1
            db.session.commit()
            return jsonify({
                'action': 'changed',
                'likes': video.likes_count,
                'dislikes': video.dislikes_count,
                'user_reaction': reaction_type
            }), 200
    else:
        reaction = VideoReaction(video_id=video_id, user_id=user.id, reaction_type=reaction_type)
        if reaction_type == 'like':
            video.likes_count += 1
        else:
            video.dislikes_count += 1
        db.session.add(reaction)
        db.session.commit()
        return jsonify({
            'action': 'added',
            'likes': video.likes_count,
            'dislikes': video.dislikes_count,
            'user_reaction': reaction_type
        }), 200


@reactions_bp.route('/videos/<int:video_id>/reaction', methods=['GET'])
@require_auth
def get_my_reaction(video_id):
    user = request.current_user
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404
    existing = VideoReaction.query.filter_by(video_id=video_id, user_id=user.id).first()
    return jsonify({
        'likes': video.likes_count,
        'dislikes': video.dislikes_count,
        'user_reaction': existing.reaction_type if existing else None
    }), 200


@reactions_bp.route('/videos/<int:video_id>/report', methods=['POST'])
@require_auth
def report_video(video_id):
    user = request.current_user
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Video not found'}}), 404

    data = request.get_json()
    reason = data.get('reason', '').strip() if data else ''
    if not reason or len(reason) > 500:
        return jsonify({'error': {'code': 'BAD_REQUEST', 'message': 'Reason required (max 500 chars)'}}), 400

    existing = VideoReport.query.filter_by(video_id=video_id, user_id=user.id, status='pending').first()
    if existing:
        return jsonify({'error': {'code': 'CONFLICT', 'message': 'Already reported'}}), 409

    report = VideoReport(video_id=video_id, user_id=user.id, reason=reason)
    db.session.add(report)
    db.session.commit()

    return jsonify({'message': 'Report submitted', 'id': report.id}), 201
