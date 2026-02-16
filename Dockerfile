FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLANNER_DB_PATH=/data/planner.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY templates ./templates
COPY static ./static

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 5000

CMD ["python", "app.py"]
