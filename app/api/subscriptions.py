from flask import Blueprint, request, jsonify
from app.services.subscription_service import SubscriptionService
from app.services.channel_service import ChannelService
from app.api.auth import require_auth

subscriptions_bp = Blueprint('subscriptions', __name__)

subscription_service = SubscriptionService()
channel_service = ChannelService()


@subscriptions_bp.route('/channels/<int:channel_id>/subscribe', methods=['POST'])
@require_auth
def subscribe_to_channel(channel_id):
    user = request.current_user

    channel = channel_service.get_channel(channel_id)
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Channel with id {channel_id} not found'
            }
        }), 404

    data = request.get_json() or {}
    is_sponsor = data.get('is_sponsor', False)

    try:
        subscription = subscription_service.subscribe(user, channel, is_sponsor)
        return jsonify(subscription_service.to_dict(subscription)), 201

    except ValueError as e:
        error_message = str(e)

        if 'already subscribed' in error_message.lower():
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


@subscriptions_bp.route('/channels/<int:channel_id>/subscribe', methods=['DELETE'])
@require_auth
def unsubscribe_from_channel(channel_id):
    user = request.current_user

    channel = channel_service.get_channel(channel_id)
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Channel with id {channel_id} not found'
            }
        }), 404

    try:
        subscription_service.unsubscribe(user, channel)
        return jsonify({
            'message': 'Unsubscribed successfully'
        }), 200

    except ValueError as e:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': str(e)
            }
        }), 404


@subscriptions_bp.route('/channels/<int:channel_id>/sponsor', methods=['POST'])
@require_auth
def upgrade_to_sponsor(channel_id):
    user = request.current_user

    channel = channel_service.get_channel(channel_id)
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Channel with id {channel_id} not found'
            }
        }), 404

    try:
        subscription = subscription_service.upgrade_to_sponsor(user, channel)
        return jsonify(subscription_service.to_dict(subscription)), 200

    except ValueError as e:
        error_message = str(e)

        if 'already a sponsor' in error_message.lower():
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


@subscriptions_bp.route('/channels/<int:channel_id>/sponsor', methods=['DELETE'])
@require_auth
def downgrade_from_sponsor(channel_id):
    user = request.current_user

    channel = channel_service.get_channel(channel_id)
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Channel with id {channel_id} not found'
            }
        }), 404

    try:
        subscription = subscription_service.downgrade_from_sponsor(user, channel)
        return jsonify(subscription_service.to_dict(subscription)), 200

    except ValueError as e:
        return jsonify({
            'error': {
                'code': 'UNPROCESSABLE_ENTITY',
                'message': str(e)
            }
        }), 422


@subscriptions_bp.route('/subscriptions/my', methods=['GET'])
@require_auth
def get_my_subscriptions_short():
    user = request.current_user
    subscriptions = subscription_service.get_user_subscriptions(user, False)

    return jsonify([
        {
            'id': sub.id,
            'user_id': sub.user_id,
            'channel_id': sub.channel_id,
            'is_sponsor': sub.is_sponsor,
            'created_at': sub.created_at.isoformat()
        }
        for sub in subscriptions
    ]), 200


@subscriptions_bp.route('/subscriptions', methods=['POST'])
@require_auth
def create_subscription():
    user = request.current_user
    data = request.get_json()

    if not data or 'channel_id' not in data:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'channel_id is required'
            }
        }), 400

    channel_id = data['channel_id']
    is_sponsor = data.get('is_sponsor', False)

    channel = channel_service.get_channel(channel_id)
    if not channel:
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': f'Channel with id {channel_id} not found'
            }
        }), 404

    try:
        subscription = subscription_service.subscribe(user, channel, is_sponsor)
        return jsonify({
            'id': subscription.id,
            'user_id': subscription.user_id,
            'channel_id': subscription.channel_id,
            'is_sponsor': subscription.is_sponsor,
            'created_at': subscription.created_at.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({
            'error': {
                'code': 'UNPROCESSABLE_ENTITY',
                'message': str(e)
            }
        }), 422


@subscriptions_bp.route('/subscriptions/<int:subscription_id>', methods=['DELETE'])
@require_auth
def delete_subscription(subscription_id):
    user = request.current_user

    try:
        from app.models import Subscription
        subscription = Subscription.query.get(subscription_id)

        if not subscription:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Subscription not found'
                }
            }), 404

        if subscription.user_id != user.id:
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not your subscription'
                }
            }), 403

        channel = channel_service.get_channel(subscription.channel_id)
        subscription_service.unsubscribe(user, channel)

        return jsonify({
            'message': 'Unsubscribed successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


@subscriptions_bp.route('/users/me/subscriptions', methods=['GET'])
@require_auth
def get_my_subscriptions():
    user = request.current_user
    sponsors_only = request.args.get('sponsors_only', 'false').lower() == 'true'
    subscriptions = subscription_service.get_user_subscriptions(user, sponsors_only)
    return jsonify({
        'subscriptions': [subscription_service.to_dict(sub) for sub in subscriptions]
    }), 200


@subscriptions_bp.route('/channels/<int:channel_id>/subscribers', methods=['GET'])
@require_auth
def get_channel_subscribers(channel_id):
    channel = channel_service.get_channel(channel_id)
    if not channel:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Channel not found'}}), 404
    user = request.current_user
    if channel.author_id != user.id and not user.is_admin:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Only channel owner can view subscribers'}}), 403
    subs = subscription_service.get_channel_subscribers(channel)
    return jsonify([subscription_service.to_dict(s, include_user=True) for s in subs]), 200
