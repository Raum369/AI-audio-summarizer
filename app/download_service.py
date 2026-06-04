import os
import re
import logging
import aiohttp
import asyncio
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

class DownloadService:
    """Сервіс для асинхронного завантаження аудіо за посиланнями."""

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Перевіряє, чи є посилання посиланням на YouTube."""
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(youtube_regex.match(url))

    @classmethod
    def clean_cloud_url(cls, url: str) -> str:
        """
        Конвертує стандартні посилання на хмари (Dropbox, Google Drive) 
        у прямі посилання для завантаження файлу.
        """
        # Google Drive
        if "drive.google.com" in url:
            # Витягуємо ID файлу з посилання
            match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
            if match:
                file_id = match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
            
        # Dropbox
        if "dropbox.com" in url:
            # Замінюємо dl=0 на dl=1 для прямого скачування
            if "dl=0" in url:
                return url.replace("dl=0", "dl=1")
            elif "dl=1" not in url:
                return url + "&dl=1" if "?" in url else url + "?dl=1"
                
        return url

    @classmethod
    async def download_youtube_audio(cls, url: str, output_dir: str) -> str:
        """
        Завантажує аудіо з YouTube-відео за допомогою yt-dlp.
        Повертає локальний шлях до файлу.
        """
        logger.info(f"Завантаження аудіо з YouTube: {url}")
        
        # Налаштування для yt-dlp (завантаження найкращого аудіо в форматі m4a/mp3)
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            # Використовуємо вбудований конвертер, якщо треба, але зазвичай m4a/webm підходить
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True,
            'no_warnings': True,
        }

        # Оскільки yt-dlp синхронна бібліотека, запускаємо її в окремому потоці (thread)
        def run_ydl():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                # Оскільки ми просили mp3, розширення зміниться на mp3
                base = os.path.splitext(filename)[0]
                return f"{base}.mp3"

        loop = asyncio.get_event_loop()
        mp3_path = await loop.run_in_executor(None, run_ydl)
        logger.info(f"Аудіо з YouTube успішно завантажено в: {mp3_path}")
        return mp3_path

    @classmethod
    async def download_direct_file(cls, url: str, output_dir: str) -> str:
        """
        Завантажує файл за прямим URL-посиланням.
        Повертає локальний шлях до файлу.
        """
        url = cls.clean_cloud_url(url)
        logger.info(f"Завантаження файлу за прямим посиланням: {url}")
        
        # Спробуємо витягнути назву файлу з URL або дамо дефолтну
        file_name = url.split('/')[-1].split('?')[0]
        if not file_name or '.' not in file_name:
            file_name = "downloaded_audio.mp3"
            
        dest_path = os.path.join(output_dir, file_name)
        os.makedirs(output_dir, exist_ok=True)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    raise Exception(f"Не вдалося завантажити файл. HTTP Статус: {response.status}")
                
                # Записуємо чанками, щоб не перевантажувати оперативну пам'ять
                with open(dest_path, "wb") as f:
                    while True:
                        chunk = await response.content.read(1024 * 1024) # 1 MB
                        if not chunk:
                            break
                        f.write(chunk)
                        
        logger.info(f"Файл успішно завантажено за посиланням: {dest_path}")
        return dest_path
