from flask import Blueprint, render_template, send_from_directory, current_app
import os

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    return render_template('index.html')


@web_bp.route('/video/<int:video_id>')
def video_player(video_id):
    return render_template('video_player.html', video_id=video_id)


@web_bp.route('/channel/<int:channel_id>')
def channel_page(channel_id):
    return render_template('channel.html', channel_id=channel_id)


@web_bp.route('/rooms')
def rooms_list():
    return render_template('rooms.html')


@web_bp.route('/room/<int:room_id>')
def room_page(room_id):
    return render_template('room.html', room_id=room_id)


@web_bp.route('/profile/<int:user_id>')
def profile_page(user_id):
    return render_template('profile.html', user_id=user_id)


@web_bp.route('/messages')
def messages_page():
    return render_template('messages.html')


@web_bp.route('/admin')
def admin_page():
    return render_template('admin.html')


@web_bp.route('/terms')
def terms_page():
    return render_template('terms.html')


@web_bp.route('/privacy')
def privacy_page():
    return render_template('privacy.html')


@web_bp.route('/videos/<path:filename>')
def serve_video(filename):
    video_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(video_folder, filename)


@web_bp.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    thumb_folder = current_app.config['THUMBNAIL_FOLDER']
    return send_from_directory(thumb_folder, filename)
