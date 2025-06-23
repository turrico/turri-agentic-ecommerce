FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set default PORT if not provided (useful for local dev)
ENV PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install --no-cache-dir --upgrade uv
RUN uv sync

COPY ./src ./src
EXPOSE ${PORT}
# currently in live development mode
CMD ["sh", "-c", "uv run uvicorn src.api.main:app --port ${PORT} --host 0.0.0.0"]
