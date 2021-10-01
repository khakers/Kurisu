FROM python:3.8.5-slim as builder


RUN apt-get update \
    && apt-get install -y git \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*


COPY . /app/

WORKDIR /app/

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root --no-interaction --no-ansi \
    && pip uninstall -y poetry \
    && rm -rf /root/.cache/*


FROM python:3.8.5-slim

COPY --from=builder /usr/local /usr/local

COPY . /app/

WORKDIR /app/

# The file must exist to be overriden
RUN touch config.toml

ENTRYPOINT [ "python3", "main.py" ]