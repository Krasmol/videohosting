from typing import Optional, List, Dict, Any
from app import db
from app.models import Subscription, User, Channel


class SubscriptionService:

    @staticmethod
    def subscribe(user: User, channel: Channel, is_sponsor: bool = False) -> Subscription:
        if channel.author_id == user.id:
            raise ValueError("Cannot subscribe to your own channel")

        existing = Subscription.query.filter_by(
            user_id=user.id,
            channel_id=channel.id
        ).first()

        if existing:
            raise ValueError("Already subscribed to this channel")

        subscription = Subscription(
            user_id=user.id,
            channel_id=channel.id,
            is_sponsor=is_sponsor
        )

        db.session.add(subscription)
        db.session.commit()

        return subscription

    @staticmethod
    def unsubscribe(user: User, channel: Channel) -> bool:
        subscription = Subscription.query.filter_by(
            user_id=user.id,
            channel_id=channel.id
        ).first()

        if not subscription:
            raise ValueError("Subscription not found")

        db.session.delete(subscription)
        db.session.commit()

        return True

    @staticmethod
    def upgrade_to_sponsor(user: User, channel: Channel) -> Subscription:
        subscription = Subscription.query.filter_by(
            user_id=user.id,
            channel_id=channel.id
        ).first()

        if not subscription:
            raise ValueError("Must be subscribed before upgrading to sponsor")

        if subscription.is_sponsor:
            raise ValueError("Already a sponsor of this channel")

        subscription.is_sponsor = True
        db.session.commit()

        return subscription

    @staticmethod
    def downgrade_from_sponsor(user: User, channel: Channel) -> Subscription:
        subscription = Subscription.query.filter_by(
            user_id=user.id,
            channel_id=channel.id
        ).first()

        if not subscription:
            raise ValueError("Subscription not found")

        if not subscription.is_sponsor:
            raise ValueError("Not a sponsor of this channel")

        subscription.is_sponsor = False
        db.session.commit()

        return subscription

    @staticmethod
    def is_subscribed(user: User, channel: Channel) -> bool:
        subscription = Subscription.query.filter_by(
            user_id=user.id,
            channel_id=channel.id
        ).first()

        return subscription is not None

    @staticmethod
    def is_sponsor(user: User, channel: Channel) -> bool:
        subscription = Subscription.query.filter_by(
            user_id=user.id,
            channel_id=channel.id
        ).first()

        return subscription is not None and subscription.is_sponsor

    @staticmethod
    def get_user_subscriptions(user: User, sponsors_only: bool = False) -> List[Subscription]:
        query = Subscription.query.filter_by(user_id=user.id)

        if sponsors_only:
            query = query.filter_by(is_sponsor=True)

        return query.order_by(Subscription.created_at.desc()).all()

    @staticmethod
    def get_channel_subscribers(channel: Channel, sponsors_only: bool = False) -> List[Subscription]:
        query = Subscription.query.filter_by(channel_id=channel.id)

        if sponsors_only:
            query = query.filter_by(is_sponsor=True)

        return query.order_by(Subscription.created_at.desc()).all()

    @staticmethod
    def to_dict(subscription: Subscription, include_channel: bool = True, include_user: bool = False) -> Dict[str, Any]:
        data = {
            'id': subscription.id,
            'user_id': subscription.user_id,
            'channel_id': subscription.channel_id,
            'is_sponsor': subscription.is_sponsor,
            'created_at': subscription.created_at.isoformat()
        }

        if include_channel and subscription.channel:
            data['channel'] = {
                'id': subscription.channel.id,
                'name': subscription.channel.name,
                'description': subscription.channel.description,
                'author_id': subscription.channel.author_id
            }

        if include_user and subscription.user:
            data['user'] = {
                'id': subscription.user.id,
                'username': subscription.user.username
            }

        return data
