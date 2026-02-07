FROM python:3.13-slim

# نصب ffmpeg برای merge ویدیو+صدا در yt-dlp
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نصب وابستگی‌ها
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# کپی کل پروژه
COPY . /app

# اجرای بات (مثل Railpack)
CMD ["python", "-m", "bot.main"]
