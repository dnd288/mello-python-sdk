FROM python:3.12-slim

# Avoid writing .pyc files and enable unbuffered stdout/stderr for logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first to leverage Docker layer caching.
COPY pyproject.toml README.md LICENSE ./
COPY mello ./mello

# Install the package together with the MCP extra.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[mcp]"

# HTTP transport defaults for running inside a container.
ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

EXPOSE 8000

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["mello-mcp-server"]
