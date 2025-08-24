FROM python:3.10-slim

# Ishchi papka yaratamiz
WORKDIR /app

# Kutubxonalarni o‘rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni ko‘chiramiz
COPY . .

# Botni ishga tushiramiz
CMD ["python", "bot.py"]
