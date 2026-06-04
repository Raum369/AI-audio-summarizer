# AI Audio Summarizer 🎙️📄

An intelligent Telegram bot designed to transcribe audio files, voice messages, cloud links, and YouTube videos, generating highly structured meeting minutes and action items (TL;DR, key topics, decisions, tasks with deadlines) in markdown format.

Powered by **Groq Whisper** for fast, high-quality audio transcription and **Llama 3.3** for automated analytical summaries.

---

## 🌟 Key Features

* **Voice Notes Processing**: Instantly records and processes Telegram voice messages (`.ogg` format).
* **Direct Audio Uploads**: Supports major audio formats (`.mp3`, `.m4a`, `.wav`, etc.) up to 20MB directly through Telegram.
* **Large File Handler**: Automatically splits audio files larger than 24MB into 15-minute chunks, transcribes them sequentially, and merges the output into a single summary.
* **External Link Downloader**: Bypasses Telegram's file size limits by downloading directly from public cloud storage links (Google Drive, Dropbox, OneDrive) or fetching audio tracks from YouTube videos.
* **Smart Markdown Reports**: Generates professional meeting protocols containing:
  - **TL;DR**: High-level summary of the meeting.
  - **Key Topics**: Breakdown of key discussions and details.
  - **Decisions**: List of agreed-upon solutions.
  - **Action Items**: To-do tasks with assigned owners and deadlines.

---

## 🛠️ Tech Stack

* **Language**: Python 3.10+
* **Framework**: [Aiogram 3.x](https://github.com/aiogram/aiogram) (Asynchronous Telegram Bot API wrapper)
* **AI Models**:
  - Speech-To-Text: `whisper-large-v3` via [Groq API](https://groq.com/)
  - Summarization: `llama-3.3-70b-versatile` via Groq API
* **Audio Utilities**: [PyDub](https://github.com/jiaaro/pydub) (for format conversion and chunk splitting)
* **Link Downloader**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) & `aiohttp`

---

## 🚀 Quick Start

### 1. Prerequisites

Make sure you have **Python 3.10+** and **FFmpeg** installed on your system.
* **FFmpeg Installation**:
  - *Windows*: Install via Chocolatey `choco install ffmpeg` or download binaries from [ffmpeg.org](https://ffmpeg.org/) and add them to your System PATH.
  - *macOS*: `brew install ffmpeg`
  - *Linux*: `sudo apt install ffmpeg`

### 2. Installation

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/Raum369/AI-audio-summarizer.git
cd AI-audio-summarizer
```

Create and activate a virtual environment:

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the root folder (copied from `.env.example` if available, or created manually):

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
```

### 4. Running the Bot

Start the application:

```bash
python -m app.main
```

---

## 📂 Project Structure

```text
├── app/
│   ├── __init__.py
│   ├── main.py                # Bot startup script
│   ├── config.py              # Configuration & env parser (Pydantic settings)
│   ├── bot.py                 # Telegram handlers & core message router
│   ├── audio_service.py       # Audio conversion & slicing (PyDub wrapper)
│   ├── transcribe_service.py  # Audio transcription interface (Groq Whisper)
│   ├── ai_service.py          # Summary generator (Llama 3.3 integration)
│   └── download_service.py    # YouTube and cloud URL fetcher
├── downloads/                 # Temporary storage for downloaded/processed audio files (ignored by Git)
├── .gitignore
├── requirements.txt
└── README.md
```
