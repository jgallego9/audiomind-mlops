FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv

ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml ./
RUN uv pip install --no-cache -r pyproject.toml

COPY app/ ./app/

VOLUME ["/models"]

EXPOSE 8080

CMD ["python", "-m", "app.main"]
