FROM python:3.12-slim

WORKDIR /app

# Copy package files
COPY pyproject.toml .
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir .

# Run the MCP server
ENTRYPOINT ["loki-mcp"]
