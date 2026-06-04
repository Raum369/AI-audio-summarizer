import os
import logging
from typing import Optional
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.config import settings
from app.audio_service import AudioService
from app.transcribe_service import TranscribeService
from app.ai_service import AIService
from app.download_service import DownloadService

logger = logging.getLogger(__name__)

# Ініціалізація бота
bot = Bot(
    token=settings.telegram_bot_token.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()

# Ініціалізація сервісів
transcribe_service = TranscribeService()
ai_service = AIService()

DOWNLOADS_DIR = "downloads"

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    """Обробник команди /start."""
    welcome_text = (
        "🎙️ **Вітаю в AI Meeting Summarizer!**\n\n"
        "Я допоможу тобі швидко створити протокол зустрічі та список завдань (Action Items).\n\n"
        "**Як мною користуватися:**\n"
        "1. Запиши та надішли мені голосове повідомлення (Voice note).\n"
        "2. Або завантаж аудіофайл зустрічі (підтримуються `.mp3`, `.m4a`, `.wav`, `.ogg` тощо).\n\n"
        "Я розпізнаю голос через **Groq Whisper**, виділю ключові рішення та доручення за допомогою **Llama 3.3** "
        "і надішлю тобі структурований звіт!"
    )
    await message.answer(welcome_text)

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    """Обробник команди /help."""
    help_text = (
        "⚙️ **Як працює обробка аудіо:**\n"
        "* Менші файли обробляються майже миттєво.\n"
        "* Якщо аудіофайл великий (більше 24 МБ), я автоматично наріжу його на частини по 15 хвилин, "
        "розпізнаю кожну частину та об'єднаю їх у загальний документ.\n"
        "* Результат ти отримаєш у вигляді повідомлення та файлу протоколу `.md`.\n"
        "* Також ви можете надіслати мені **посилання на YouTube або файл у хмарі**!"
    )
    await message.answer(help_text)


async def process_local_audio_file(message: types.Message, local_path: str, display_name: str, status_msg: types.Message):
    """Ядро обробки аудіофайлу: конвертація, Whisper розпізнання, Llama аналіз."""
    mp3_path = None
    try:
        # 1. Конвертуємо у MP3 формат
        await status_msg.edit_text("🎛️ **Оптимізую аудіоформат...**")
        mp3_path = AudioService.convert_to_mp3(local_path)
        
        # Видаляємо вихідний завантажений файл, якщо він відрізняється від mp3_path
        if local_path != mp3_path and os.path.exists(local_path):
            os.remove(local_path)
            
        # 2. Розбиваємо на чанки, якщо файл великий
        await status_msg.edit_text("✂️ **Перевіряю ліміти розміру файлу...**")
        audio_chunks = AudioService.chunk_audio_if_needed(mp3_path)
        
        # 3. Транскрибуємо аудіо
        await status_msg.edit_text(f"🎙️ **Розпізнаю мову (Groq Whisper)...**\n*Оброблено чанків: 0 з {len(audio_chunks)}*")
        
        results = []
        for i, chunk in enumerate(audio_chunks):
            if i > 0:
                await status_msg.edit_text(
                    f"🎙️ **Розпізнаю мову (Groq Whisper)...**\n*Оброблено чанків: {i} з {len(audio_chunks)} (пауза 2с для лімітів API)*"
                )
                import asyncio
                await asyncio.sleep(2)
                
            text = await transcribe_service.transcribe_file(chunk)
            results.append(text)
            
            # Видаляємо чанк після розпізнання
            if os.path.exists(chunk):
                os.remove(chunk)
                
        full_transcript = "\n\n".join(results)
        
        if not full_transcript.strip():
            await status_msg.edit_text("❌ Не вдалося розпізнати мову у файлі. Спробуйте інший запис.")
            return

        # 4. Аналізуємо текст через LLM
        await status_msg.edit_text("🤖 **ШІ аналізує стенограму (Llama 3.3)...**\n*Виділяю теми, рішення та завдання...*")
        meeting_summary = await ai_service.summarize_meeting(full_transcript)
        
        # 5. Форматуємо результат
        markdown_report = AIService.format_summary_to_markdown(meeting_summary)
        
        # 6. Відправляємо результат
        await status_msg.delete()
        
        short_summary_text = (
            f"🎯 **Короткий огляд зустрічі (TL;DR):**\n{meeting_summary.summary}\n\n"
            f"✅ **Кількість завдань (Action Items):** {len(meeting_summary.action_items)}\n"
            f"🤝 **Прийнято рішень:** {len(meeting_summary.decisions)}"
        )
        await message.answer(short_summary_text)
        
        # Зберігаємо повний звіт у файл та відправляємо його
        report_file_name = f"Report_{os.path.splitext(display_name)[0]}.md"
        report_file_path = os.path.join(DOWNLOADS_DIR, report_file_name)
        
        with open(report_file_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)
            
        await message.answer_document(
            types.FSInputFile(report_file_path, filename=report_file_name),
            caption="📄 Повний протокол зустрічі та завдання (Markdown-файл)"
        )
        
        if os.path.exists(report_file_path):
            os.remove(report_file_path)

    except Exception as e:
        logger.error(f"Помилка при обробці аудіо-повідомлення: {e}")
        await status_msg.edit_text("❌ **Виникла помилка під час обробки.**\nПеревірте логи бота.")
    finally:
        # Завжди чистимо mp3_path
        if mp3_path and os.path.exists(mp3_path):
            os.remove(mp3_path)
        if os.path.exists(local_path):
            os.remove(local_path)


async def process_audio_message(message: types.Message, file_id: str, file_name: str, file_size: Optional[int] = None):
    """Обробка файлів, завантажених безпосередньо з Telegram."""
    MAX_TELEGRAM_DOWNLOAD_SIZE = 20 * 1024 * 1024
    
    if file_size and file_size > MAX_TELEGRAM_DOWNLOAD_SIZE:
        await message.answer(
            f"⚠️ **Файл завеликий!** ({file_size / 1024 / 1024:.2f} MB)\n\n"
            f"Через обмеження Telegram Bot API, боти можуть завантажувати файли розміром лише **до 20 MB**.\n"
            f"Будь ласка, розділіть файл на менші частини або надішліть посилання на цей файл у хмарі (Google Drive / Dropbox)."
        )
        return

    status_msg = await message.answer("📥 **Завантажую аудіофайл з Telegram...** Будь ласка, зачекайте.")
    local_path = os.path.join(DOWNLOADS_DIR, file_name)
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    try:
        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, local_path)
        await process_local_audio_file(message, local_path, file_name, status_msg)
    except Exception as e:
        logger.error(f"Не вдалося завантажити файл з Telegram: {e}")
        await status_msg.edit_text("❌ **Не вдалося завантажити файл з серверів Telegram.**")
        if os.path.exists(local_path):
            os.remove(local_path)


@dp.message(F.text & F.text.startswith("http"))
async def link_handler(message: types.Message):
    """Обробник повідомлень, що містять посилання (HTTP/HTTPS)."""
    url = message.text.strip()
    status_msg = await message.answer("🔍 **Аналізую посилання...**")
    
    try:
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        
        # 1. Перевіряємо, чи це YouTube
        if DownloadService.is_youtube_url(url):
            await status_msg.edit_text("🎥 **Виявлено посилання на YouTube.** Завантажую аудіо-доріжку...")
            local_path = await DownloadService.download_youtube_audio(url, DOWNLOADS_DIR)
            display_name = os.path.basename(local_path)
        else:
            # 2. Пряме скачування файлу
            await status_msg.edit_text("📥 **Виявлено пряме посилання.** Завантажую файл...")
            local_path = await DownloadService.download_direct_file(url, DOWNLOADS_DIR)
            display_name = os.path.basename(local_path)

        # 3. Передаємо локальний файл у ядро обробки
        await process_local_audio_file(message, local_path, display_name, status_msg)

    except Exception as e:
        logger.error(f"Помилка при завантаженні за посиланням: {e}")
        await status_msg.edit_text(f"❌ **Не вдалося завантажити аудіо за посиланням.**\nПереконайтеся, що це пряме посилання на файл або YouTube-відео.\n\n*Деталі: {str(e)}*")


@dp.message(F.voice)
async def voice_handler(message: types.Message):
    """Обробник голосових повідомлень."""
    file_id = message.voice.file_id
    file_name = f"voice_{message.voice.file_unique_id}.ogg"
    file_size = message.voice.file_size
    await process_audio_message(message, file_id, file_name, file_size)


@dp.message(F.audio)
async def audio_handler(message: types.Message):
    """Обробник прикріплених аудіофайлів."""
    file_id = message.audio.file_id
    orig_name = message.audio.file_name or f"audio_{message.audio.file_unique_id}.mp3"
    file_size = message.audio.file_size
    await process_audio_message(message, file_id, orig_name, file_size)


@dp.message(F.document & F.document.mime_type.startswith("audio/"))
async def audio_document_handler(message: types.Message):
    """Обробник файлів, які є аудіозаписами, але надіслані як документи."""
    file_id = message.document.file_id
    orig_name = message.document.file_name or f"doc_{message.document.file_unique_id}.mp3"
    file_size = message.document.file_size
    await process_audio_message(message, file_id, orig_name, file_size)
