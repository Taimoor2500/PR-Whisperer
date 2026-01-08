# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

