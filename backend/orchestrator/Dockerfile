FROM python:3.10-slim
WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/orchestrator /app/backend/orchestrator
RUN pip install --no-cache-dir pydantic fastapi uvicorn python-dotenv httpx google-generativeai openai pandas psycopg2-binary
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["python", "backend/orchestrator/main.py"]
