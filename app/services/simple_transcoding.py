import os
import subprocess
import threading
import logging
from flask import current_app
from app import db
from app.models import Video

logger = logging.getLogger(__name__)


class SimpleTranscodingService:
    """Простой сервис транскодирования без Celery"""

    @staticmethod
    def transcode_to_webm(video_id: int):
        """Конвертировать видео в WebM VP9 в фоновом потоке"""
        logger.info(f'Starting transcoding for video {video_id}')
        # Получаем текущий app для передачи в поток
        app = current_app._get_current_object()
        thread = threading.Thread(target=SimpleTranscodingService._transcode_worker, args=(video_id, app))
        thread.daemon = True
        thread.start()

    @staticmethod
    def _transcode_worker(video_id: int, app):
        """Рабочий поток для транскодирования"""
        try:
            # Используем переданный app вместо создания нового
            with app.app_context():
                video = Video.query.get(video_id)
                if not video:
                    logger.error(f'Video {video_id} not found')
                    return

                if not video.file_path or not os.path.exists(video.file_path):
                    logger.error(f'Video file not found: {video.file_path}')
                    return

                # Путь к оригиналу
                original_path = video.file_path
                logger.info(f'Transcoding video {video_id} from {original_path}')

                # Путь для WebM версии
                base_name = os.path.splitext(os.path.basename(original_path))[0]
                webm_folder = os.path.join(os.path.dirname(original_path), '..', 'transcoded')
                webm_folder = os.path.abspath(webm_folder)
                os.makedirs(webm_folder, exist_ok=True)

                webm_path = os.path.join(webm_folder, f"{base_name}.webm")
                logger.info(f'Output path: {webm_path}')

                # Конвертировать в WebM VP9
                cmd = [
                    'ffmpeg', '-y',
                    '-i', original_path,
                    '-c:v', 'libvpx-vp9',
                    '-crf', '30',
                    '-b:v', '0',
                    '-c:a', 'libopus',
                    '-b:a', '128k',
                    '-threads', '2',
                    webm_path
                ]

                logger.info(f'Running ffmpeg command: {" ".join(cmd)}')
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0 and os.path.exists(webm_path):
                    logger.info(f'Transcoding completed successfully for video {video_id}')
                    # Обновить запись в базе
                    video.transcoded_480p_webm = webm_path
                    video.transcoding_status = 'completed'
                    db.session.commit()
                else:
                    error_msg = result.stderr if result.stderr else 'FFmpeg conversion failed'
                    logger.error(f'Transcoding failed for video {video_id}: {error_msg}')
                    video.transcoding_status = 'failed'
                    video.transcoding_error = error_msg[:500]
                    db.session.commit()

        except Exception as e:
            logger.exception(f'Exception during transcoding video {video_id}: {str(e)}')
            try:
                with app.app_context():
                    video = Video.query.get(video_id)
                    if video:
                        video.transcoding_status = 'failed'
                        video.transcoding_error = str(e)[:500]
                        db.session.commit()
            except:
                pass
