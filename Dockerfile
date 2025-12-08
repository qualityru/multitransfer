FROM python:3.13-slim-bullseye
COPY . /app
WORKDIR /app
# VOLUME /app/static
RUN pip install -r requirements.txt
CMD gunicorn app:app \
    --workers 4 \
    --bind 0.0.0.0:8015 \
    --max-requests 1000 \
    --timeout 30 \
    --graceful-timeout 30 \
    --keep-alive 75 \
    --worker-class uvicorn.workers.UvicornWorker

