import os
import logging
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class AudioService:
    """Сервіс для конвертації та нарізки аудіофайлів."""

    # Максимальний розмір файлу для Groq Whisper API (у байтах). Ліміт 25MB, беремо 24MB для безпеки.
    MAX_FILE_SIZE_BYTES = 24 * 1024 * 1024

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Повертає розмір файлу в байтах."""
        return os.path.getsize(file_path)

    @classmethod
    def convert_to_mp3(cls, input_path: str) -> str:
        """
        Конвертує аудіо в MP3 формат.
        Підтримує .ogg (Telegram voice), .m4a (iPhone), .wav тощо.
        Гарантує, що розширення підсумкового файлу буде строго в нижньому регістрі (.mp3).
        """
        actual_ext = os.path.splitext(input_path)[1]
        file_ext = actual_ext.lower()
        
        # Якщо файл уже має розширення mp3
        if file_ext == ".mp3":
            # Але розширення записане великими літерами (наприклад, .Mp3 або .MP3)
            if actual_ext != ".mp3":
                output_path = os.path.splitext(input_path)[0] + ".mp3"
                logger.info(f"Перейменовуємо файл для відповідності регістру: {input_path} -> {output_path}")
                try:
                    if os.path.exists(input_path):
                        os.rename(input_path, output_path)
                    return output_path
                except Exception as e:
                    logger.error(f"Помилка при перейменуванні файлу: {e}")
            return input_path

        output_path = os.path.splitext(input_path)[0] + ".mp3"
        logger.info(f"Конвертуємо {input_path} -> {output_path}")

        try:
            # Для pydub потрібен встановлений ffmpeg в системі. 
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format="mp3", bitrate="128k")
            
            # Видаляємо оригінальний файл після конвертації
            if input_path != output_path and os.path.exists(input_path):
                os.remove(input_path)
                
            return output_path
        except Exception as e:
            logger.error(f"Помилка конвертації аудіо: {e}")
            # Якщо виникла помилка, перевіримо чи не треба хоча б перейменувати розширення оригінального файлу
            if actual_ext != ".mp3":
                fallback_path = os.path.splitext(input_path)[0] + ".mp3"
                try:
                    if os.path.exists(input_path):
                        os.rename(input_path, fallback_path)
                    return fallback_path
                except Exception as rename_err:
                    logger.error(f"Помилка при спробі аварійного перейменування: {rename_err}")
            return input_path

    @classmethod
    def chunk_audio_if_needed(cls, file_path: str) -> list[str]:
        """
        Перевіряє розмір файлу. Якщо він > 24MB, нарізає його на частини
        та повертає список шляхів до створених чанків.
        """
        file_size = cls.get_file_size(file_path)
        if file_size <= cls.MAX_FILE_SIZE_BYTES:
            logger.info(f"Файл {file_path} підходить за розміром ({file_size / 1024 / 1024:.2f} MB)")
            return [file_path]

        logger.info(f"Файл {file_path} завеликий ({file_size / 1024 / 1024:.2f} MB). Починаємо нарізання...")
        
        try:
            audio = AudioSegment.from_file(file_path)
            duration_ms = len(audio)
            
            # Розраховуємо кількість частин. Наприклад, нарізаємо частинами по 15 хвилин.
            chunk_duration_ms = 15 * 60 * 1000  # 15 хвилин
            chunks = []
            
            base_name = os.path.splitext(file_path)[0]
            
            for i, start_ms in enumerate(range(0, duration_ms, chunk_duration_ms)):
                end_ms = min(start_ms + chunk_duration_ms, duration_ms)
                chunk = audio[start_ms:end_ms]
                
                chunk_path = f"{base_name}_part{i+1}.mp3"
                chunk.export(chunk_path, format="mp3", bitrate="64k") # Зменшуємо бітрейт для меншого розміру
                chunks.append(chunk_path)
                logger.info(f"Створено чанк: {chunk_path} ({len(chunk)/1000:.1f} сек)")
                
            # Видаляємо великий вихідний файл після нарізання
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return chunks
        except Exception as e:
            logger.error(f"Помилка при нарізанні файлу: {e}")
            # У разі критичної помилки повертаємо файл як є
            return [file_path]
