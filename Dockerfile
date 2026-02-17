FROM python:3.11-slim

# FFmpeg o'rnatish (yuqori sifatli videolar va MP3 ga rasm qo'shish uchun shart)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render kutadigan portni ochish
EXPOSE 10000

CMD ["python", "bot.py"]