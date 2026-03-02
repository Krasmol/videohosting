"""Celery задачі для транскодування відео"""
import os
from celery import Celery
from app import db
from app.models import Video
from app.services.transcoding_service import TranscodingService

# Ініціалізація Celery (буде підключено до Flask app)
celery = Celery('videohost')


@celery.task(bind=True)
def transcode_video_task(self, video_id: int):
    """
    Фонова задача для транскодування відео в різні якості

    Args:
        video_id: ID відео для транскодування
    """
    from app import create_app
    app = create_app()

    with app.app_context():
        video = Video.query.get(video_id)
        if not video:
            return {'error': 'Video not found'}

        transcoding_service = TranscodingService()

        # Перевірити доступність FFmpeg
        if not transcoding_service.check_ffmpeg_available():
            video.transcoding_status = 'failed'
            video.transcoding_error = 'FFmpeg not available'
            db.session.commit()
            return {'error': 'FFmpeg not available'}

        try:
            # Оновити статус
            video.transcoding_status = 'processing'
            video.transcoding_progress = 0
            db.session.commit()

            # Шляхи до файлів
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads/videos')
            originals_folder = os.path.join(upload_folder, 'originals')
            transcoded_folder = os.path.join(upload_folder, 'transcoded')

            os.makedirs(originals_folder, exist_ok=True)
            os.makedirs(transcoded_folder, exist_ok=True)

            # Перемістити оригінал
            original_path = os.path.join(upload_folder, os.path.basename(video.file_path))
            video_basename = os.path.splitext(os.path.basename(video.file_path))[0]
            new_original_path = os.path.join(originals_folder, os.path.basename(video.file_path))

            if os.path.exists(original_path) and not os.path.exists(new_original_path):
                os.rename(original_path, new_original_path)

            video.original_file_path = f"originals/{os.path.basename(video.file_path)}"
            db.session.commit()

            # Налаштування якості
            quality_settings = transcoding_service.get_quality_settings()

            # Транскодування 360p WebM
            video.transcoding_progress = 10
            db.session.commit()

            output_360p = os.path.join(transcoded_folder, f"{video_basename}_360p.webm")
            settings_360p = quality_settings['360p']
            success_360p = transcoding_service.transcode_to_webm_vp9(
                new_original_path,
                output_360p,
                settings_360p['width'],
                settings_360p['height'],
                settings_360p['video_bitrate_webm'],
                settings_360p['audio_bitrate_webm']
            )

            if success_360p:
                video.transcoded_360p_webm = f"transcoded/{video_basename}_360p.webm"
                video.transcoding_progress = 30
                db.session.commit()

            # Транскодування 480p WebM
            output_480p_webm = os.path.join(transcoded_folder, f"{video_basename}_480p.webm")
            settings_480p = quality_settings['480p']
            success_480p_webm = transcoding_service.transcode_to_webm_vp9(
                new_original_path,
                output_480p_webm,
                settings_480p['width'],
                settings_480p['height'],
                settings_480p['video_bitrate_webm'],
                settings_480p['audio_bitrate_webm']
            )

            if success_480p_webm:
                video.transcoded_480p_webm = f"transcoded/{video_basename}_480p.webm"
                video.transcoding_progress = 50
                db.session.commit()

            # Транскодування 720p WebM
            output_720p = os.path.join(transcoded_folder, f"{video_basename}_720p.webm")
            settings_720p = quality_settings['720p']
            success_720p = transcoding_service.transcode_to_webm_vp9(
                new_original_path,
                output_720p,
                settings_720p['width'],
                settings_720p['height'],
                settings_720p['video_bitrate_webm'],
                settings_720p['audio_bitrate_webm']
            )

            if success_720p:
                video.transcoded_720p_webm = f"transcoded/{video_basename}_720p.webm"
                video.transcoding_progress = 70
                db.session.commit()

            # Транскодування 480p MP4 (fallback для Safari)
            output_480p_mp4 = os.path.join(transcoded_folder, f"{video_basename}_480p.mp4")
            success_480p_mp4 = transcoding_service.transcode_to_h264_mp4(
                new_original_path,
                output_480p_mp4,
                settings_480p['width'],
                settings_480p['height'],
                settings_480p['video_bitrate_mp4'],
                settings_480p['audio_bitrate_mp4']
            )

            if success_480p_mp4:
                video.transcoded_480p_mp4 = f"transcoded/{video_basename}_480p.mp4"
                video.transcoding_progress = 90
                db.session.commit()

            # Перевірити чи хоча б одне транскодування успішне
            if success_480p_webm or success_480p_mp4:
                video.transcoding_status = 'completed'
                video.transcoding_progress = 100
                video.status = 'ready'
            else:
                video.transcoding_status = 'failed'
                video.transcoding_error = 'All transcoding attempts failed'

            db.session.commit()

            return {
                'status': video.transcoding_status,
                'progress': video.transcoding_progress,
                'transcoded_files': {
                    '360p_webm': video.transcoded_360p_webm,
                    '480p_webm': video.transcoded_480p_webm,
                    '720p_webm': video.transcoded_720p_webm,
                    '480p_mp4': video.transcoded_480p_mp4
                }
            }

        except Exception as e:
            video.transcoding_status = 'failed'
            video.transcoding_error = str(e)
            db.session.commit()
            return {'error': str(e)}
