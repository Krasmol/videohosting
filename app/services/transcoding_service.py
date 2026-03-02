"""Сервіс транскодування відео через FFmpeg"""
import os
import subprocess
from typing import Optional, Dict
from flask import current_app


class TranscodingService:
    """Сервіс для транскодування відео в різні формати та якості"""

    @staticmethod
    def transcode_to_webm_vp9(input_path: str, output_path: str, width: int, height: int,
                               video_bitrate: str, audio_bitrate: str) -> bool:
        """
        Транскодування відео в WebM VP9

        Args:
            input_path: Шлях до вхідного файлу
            output_path: Шлях до вихідного файлу
            width: Ширина відео
            height: Висота відео
            video_bitrate: Бітрейт відео (наприклад, '500k')
            audio_bitrate: Бітрейт аудіо (наприклад, '96k')

        Returns:
            True якщо успішно, False якщо помилка
        """
        try:
            # Розрахувати maxrate та bufsize
            bitrate_value = int(video_bitrate.replace('k', ''))
            maxrate = f"{int(bitrate_value * 1.2)}k"
            bufsize = f"{int(bitrate_value * 2.4)}k"

            cmd = [
                'ffmpeg', '-y',  # Перезаписати якщо існує
                '-i', input_path,
                '-vf', f'scale={width}:{height}',
                '-c:v', 'libvpx-vp9',
                '-b:v', video_bitrate,
                '-maxrate', maxrate,
                '-bufsize', bufsize,
                '-c:a', 'libopus',
                '-b:a', audio_bitrate,
                '-deadline', 'good',
                '-cpu-used', '2',
                output_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3600  # 1 година максимум
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            current_app.logger.error(f'Transcoding timeout for {input_path}')
            return False
        except Exception as e:
            current_app.logger.error(f'Transcoding error: {str(e)}')
            return False

    @staticmethod
    def transcode_to_h264_mp4(input_path: str, output_path: str, width: int, height: int,
                               video_bitrate: str, audio_bitrate: str) -> bool:
        """
        Транскодування відео в H.264 MP4 (fallback для Safari)

        Args:
            input_path: Шлях до вхідного файлу
            output_path: Шлях до вихідного файлу
            width: Ширина відео
            height: Висота відео
            video_bitrate: Бітрейт відео
            audio_bitrate: Бітрейт аудіо

        Returns:
            True якщо успішно, False якщо помилка
        """
        try:
            bitrate_value = int(video_bitrate.replace('k', ''))
            maxrate = f"{int(bitrate_value * 1.0)}k"
            bufsize = f"{int(bitrate_value * 2.0)}k"

            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', f'scale={width}:{height}',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-maxrate', maxrate,
                '-bufsize', bufsize,
                '-c:a', 'aac',
                '-b:a', audio_bitrate,
                '-movflags', '+faststart',  # Для швидкого старту відтворення
                output_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3600
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            current_app.logger.error(f'Transcoding timeout for {input_path}')
            return False
        except Exception as e:
            current_app.logger.error(f'Transcoding error: {str(e)}')
            return False

    @staticmethod
    def get_quality_settings() -> Dict[str, Dict]:
        """Отримати налаштування якості для різних резолюцій"""
        return {
            '360p': {
                'width': 640,
                'height': 360,
                'video_bitrate_webm': '500k',
                'audio_bitrate_webm': '96k'
            },
            '480p': {
                'width': 854,
                'height': 480,
                'video_bitrate_webm': '800k',
                'video_bitrate_mp4': '1200k',
                'audio_bitrate_webm': '128k',
                'audio_bitrate_mp4': '128k'
            },
            '720p': {
                'width': 1280,
                'height': 720,
                'video_bitrate_webm': '1500k',
                'audio_bitrate_webm': '192k'
            }
        }

    @staticmethod
    def check_ffmpeg_available() -> bool:
        """Перевірити чи доступний FFmpeg"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
