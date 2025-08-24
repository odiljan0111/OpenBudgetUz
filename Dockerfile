# Python image tanlash (3.10 versiyasi barqaror)
FROM python:3.10-slim

# Container ichida ishchi papka
WORKDIR /app

# Project fayllarini copy qilish
COPY . /app

# Kutubxonalarni o‘rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Botni ishga tushirish
CMD ["python", "bot.py"]
