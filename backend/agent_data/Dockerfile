FROM python:3.10-slim
WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/agent_data /app/backend/agent_data
RUN pip install --no-cache-dir pydantic fastapi uvicorn python-dotenv httpx google-generativeai openai pandas
ENV PYTHONPATH=/app
EXPOSE 8002
CMD ["python", "backend/agent_data/main.py"]
