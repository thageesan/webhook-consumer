FROM python:3.11-slim

WORKDIR /app

RUN apt-get update -y
    
RUN set -xe \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    ca-certificates \
    python3-pip \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry==1.5.0 \
    && apt-get autoremove --assume-yes gcc

COPY ./pyproject.toml ./poetry.toml /app/
# COPY --chown=wave:wave poetry.lock /app/poetry.lock
RUN poetry install --no-root;

# Configure our virtualenv in our environment. 
# This will change the python version,  poetry name or the path of our project
# Use `poetry env info --path` to get the path.
ENV VIRTUAL_ENV=/virtualenvs/webhook-9TtSrW0h-py3.8
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
RUN if [ "$(poetry env info --path)" != "${VIRTUAL_ENV}" ]; then echo "VIRTUAL_ENV does not match poetry virtual environment"; exit 1; fi

COPY main.py /app