FROM python:3.10-slim
WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/agent_intent /app/backend/agent_intent
RUN pip install --no-cache-dir pydantic fastapi uvicorn python-dotenv httpx google-generativeai openai pandas
ENV PYTHONPATH=/app
EXPOSE 8001
CMD ["python", "backend/agent_intent/main.py"]
