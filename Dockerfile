FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "uvicorn fantasy_agent.server:app --host 0.0.0.0 --port ${PORT:-8787}"]
