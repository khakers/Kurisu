FROM python:3.8-slim as builder

RUN apt-get update -y \
    && apt-get install -y git \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

COPY ./poetry.lock /app/
COPY ./pyproject.toml /app/

WORKDIR /app/

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root --no-interaction --no-ansi \
    && pip uninstall -y poetry \
    && rm -rf /root/.cache/*


FROM python:3.8-slim

# Security updates are important
RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local

RUN useradd --create-home kurisu

COPY . /app/

WORKDIR /app/

RUN chown -R kurisu /app/

USER kurisu

# The file must exist to be overriden
RUN touch /app/config.toml

ENTRYPOINT [ "python3", "main.py" ]