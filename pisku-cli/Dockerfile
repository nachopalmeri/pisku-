FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY . .

CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}