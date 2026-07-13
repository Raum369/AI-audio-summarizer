# Використовуємо офіційний легкий образ Python
FROM python:3.11-slim

# Встановлюємо ffmpeg (критично для pydub)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо requirements і встановлюємо залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь інший код
COPY . .

# Встановлюємо порт за замовчуванням
ENV PORT=8080

# Команда для запуску нашого оновленого main.py
CMD ["python", "-m", "app.main"]
