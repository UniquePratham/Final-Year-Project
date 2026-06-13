FROM python:3.10-slim
WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/agent_report /app/backend/agent_report
RUN pip install --no-cache-dir pydantic fastapi uvicorn python-dotenv httpx google-generativeai openai pandas
ENV PYTHONPATH=/app
EXPOSE 8004
CMD ["python", "backend/agent_report/main.py"]
