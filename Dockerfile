FROM python:3.11-slim

# Prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
# Set container timezone to UTC
ENV TZ=UTC

WORKDIR /app

# Install build dependencies for pg and cryptography compile actions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project code
COPY . .

# Default container entry command (overridden for worker service in compose)
CMD ["python", "bot/main.py"]
