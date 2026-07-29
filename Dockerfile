FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn

COPY . .

EXPOSE 8000

CMD ["python3", "-m", "aris.main", "--serve", "--host", "0.0.0.0", "--port", "8000"]
