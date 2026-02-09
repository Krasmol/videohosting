from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(80), nullable=True)
    login_code = db.Column(db.String(10), unique=True, nullable=True)
    is_author = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    # Moderator is a separate role below admin.
    is_moderator = db.Column(db.Boolean, default=False, nullable=False)
    is_vip = db.Column(db.Boolean, default=False, nullable=False)
    mexels = db.Column(db.Integer, default=0, nullable=False)
    avatar_url = db.Column(db.String(500), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    channel = db.relationship('Channel', backref='author', uselist=False, cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='user', cascade='all, delete-orphan')
    owned_rooms = db.relationship('Room', backref='owner', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')
    sent_messages = db.relationship('DirectMessage', foreign_keys='DirectMessage.sender_id', backref='sender', cascade='all, delete-orphan')
    received_messages = db.relationship('DirectMessage', foreign_keys='DirectMessage.recipient_id', backref='recipient', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_display_name(self):
        return self.display_name or self.username

    def get_full_tag(self):
        code = self.login_code or '0000'
        return f"{self.get_display_name()}#{code}"

    def __repr__(self):
        return f'<User {self.username}>'


class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    banner_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    videos = db.relationship('Video', backref='channel', cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='channel', cascade='all, delete-orphan')

    @property
    def subscriber_count(self):
        return len(self.subscriptions)

    def __repr__(self):
        return f'<Channel {self.name}>'


class Video(db.Model):
    __tablename__ = 'videos'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(2000))
    file_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500), nullable=True)
    duration = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), default='other', nullable=False)
    # If true, video appears in all categories feeds.
    all_categories = db.Column(db.Boolean, default=False, nullable=False)
    tags = db.Column(db.String(500), nullable=True)
    access_level = db.Column(db.String(20), default='public', nullable=False)
    has_ads = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default='processing', nullable=False)
    views_count = db.Column(db.Integer, default=0, nullable=False)
    likes_count = db.Column(db.Integer, default=0, nullable=False)
    dislikes_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    rooms = db.relationship('Room', backref='video', cascade='all, delete-orphan')
    reactions = db.relationship('VideoReaction', backref='video', cascade='all, delete-orphan')
    reports = db.relationship('VideoReport', backref='video', cascade='all, delete-orphan')
    comments = db.relationship('VideoComment', backref='video', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Video {self.title}>'


class VideoReaction(db.Model):
    __tablename__ = 'video_reactions'

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reaction_type = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint('video_id', 'user_id', name='unique_video_user_reaction'),)

    def __repr__(self):
        return f'<VideoReaction {self.reaction_type}>'


class VideoReport(db.Model):
    __tablename__ = 'video_reports'

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<VideoReport {self.id}>'


class VideoComment(db.Model):
    __tablename__ = 'video_comments'

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User')

    def __repr__(self):
        return f'<VideoComment {self.id}>'


class ModerationLog(db.Model):
    __tablename__ = 'moderation_logs'

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False, index=True)
    moderator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(30), nullable=False)  # e.g. 'remove'
    reason_code = db.Column(db.String(50), nullable=False)
    reason_text = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    moderator = db.relationship('User')

    def __repr__(self):
        return f'<ModerationLog {self.id} action={self.action}>'


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False, index=True)
    is_sponsor = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'channel_id', name='unique_user_channel'),)

    def __repr__(self):
        return f'<Subscription user_id={self.user_id} channel_id={self.channel_id}>'


class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)
    max_participants = db.Column(db.Integer, default=10, nullable=False)
    message_delay = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    current_position = db.Column(db.Integer, default=0, nullable=False)
    is_playing = db.Column(db.Boolean, default=False, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    participants = db.relationship('RoomParticipant', backref='room', cascade='all, delete-orphan')
    invitations = db.relationship('RoomInvitation', backref='room', cascade='all, delete-orphan')
    messages = db.relationship('ChatMessage', backref='room', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Room {self.id}>'


class RoomParticipant(db.Model):
    __tablename__ = 'room_participants'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_message_at = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint('room_id', 'user_id', name='unique_room_user'),)

    def __repr__(self):
        return f'<RoomParticipant room_id={self.room_id} user_id={self.user_id}>'


class RoomInvitation(db.Model):
    __tablename__ = 'room_invitations'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<RoomInvitation {self.id} status={self.status}>'


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<ChatMessage {self.id}>'


class DirectMessage(db.Model):
    __tablename__ = 'direct_messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<DirectMessage {self.id}>'


class Advertisement(db.Model):
    __tablename__ = 'advertisements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    video_url = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    target_category = db.Column(db.String(50))

    def __repr__(self):
        return f'<Advertisement {self.title}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Notification {self.id} type={self.type}>'
