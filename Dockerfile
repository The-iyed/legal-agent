FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install semantic-kernel --upgrade


COPY . .


ENV PYTHONPATH=/app
ENV PORT=8000
ENV MONGODB_URL=mongodb://mongodb:27017
ENV MONGODB_DB_NAME=tachriat_agent


EXPOSE ${PORT}


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 