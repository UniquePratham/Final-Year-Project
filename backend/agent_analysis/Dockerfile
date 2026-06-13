FROM python:3.10-slim
WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/agent_analysis /app/backend/agent_analysis
RUN pip install --no-cache-dir pydantic fastapi uvicorn python-dotenv httpx google-generativeai openai pandas
ENV PYTHONPATH=/app
EXPOSE 8003
CMD ["python", "backend/agent_analysis/main.py"]
