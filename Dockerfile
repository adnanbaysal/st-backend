FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

RUN apt-get -y update && \
    apt-get install -y build-essential &&\
    apt-get install -y libpq-dev && \
    apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 - --version 1.6.1

ENV PATH="/etc/poetry/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

COPY social_text /app/

EXPOSE 8000

COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
