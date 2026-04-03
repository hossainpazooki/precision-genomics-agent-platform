# Dockerfile.ml — Python ML microservice
# Serves core ML algorithms via FastAPI for the TypeScript frontend

FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[ml,llm,mcp,dspy]" && \
    pip install --no-cache-dir uvicorn[standard]

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY core/ core/
COPY mcp_server/ mcp_server/
COPY dspy_modules/ dspy_modules/
COPY ml_service/ ml_service/
COPY pyproject.toml .

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "ml_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
