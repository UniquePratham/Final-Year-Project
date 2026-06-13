FROM python:3.10-slim
WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/agent_response /app/backend/agent_response
RUN pip install --no-cache-dir pydantic fastapi uvicorn python-dotenv google-generativeai openai
ENV PYTHONPATH=/app
EXPOSE 8005
CMD ["python", "backend/agent_response/main.py"]
