FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONUNBUFFERED 1

WORKDIR /clip-backend

COPY pyproject.toml poetry.lock /clip-backend/

RUN poetry install --no-root

COPY . /clip-backend/

CMD ["sh", "-c", "poetry run python manage.py migrate && \
                   poetry run python manage.py runserver 0.0.0.0:8000 & \
                   poetry run python manage.py process_tasks"]

