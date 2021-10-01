FROM python:3.8.5-slim


RUN apt-get update \
    && apt-get install -y git \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*


COPY . /app/

WORKDIR /app/

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root --no-interaction --no-ansi\
    && touch config.toml \
    && rm -rf /root/.cache/*


ENTRYPOINT [ "python3", "main.py" ]