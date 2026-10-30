FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /bin/uv
COPY --from=denoland/deno:bin-2.9.7@sha256:bc5aa4466e21b6d3021226a85ba2e1911f7c386254d97b9d797903ab74edace2 /deno /usr/local/bin/deno
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MOKA_DATA_DIR=/data
ENV UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH"
ENV DENO_DIR=/tmp/moka-deno DENO_NO_UPDATE_CHECK=1 DENO_NO_PROMPT=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg
RUN useradd --uid 10001 --create-home moka && mkdir /data && chown moka:moka /data
COPY pyproject.toml uv.lock README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable
COPY config.example.toml ./config.toml
ENV MOKA_CONFIG=/app/config.toml
USER moka
VOLUME /data
CMD ["moka", "run"]
