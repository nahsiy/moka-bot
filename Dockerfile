FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MOKA_DATA_DIR=/data
ENV UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN useradd --uid 10001 --create-home moka && mkdir /data && chown moka:moka /data
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable
COPY config.example.toml ./config.toml
ENV MOKA_CONFIG=/app/config.toml
USER moka
VOLUME /data
CMD ["moka", "run"]
