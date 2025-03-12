FROM python:3.11-alpine

WORKDIR /usr/src/app

# Copy requirements first to leverage Docker cache
COPY requirements.txt ./
RUN apk add --no-cache gcc musl-dev && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mha/ ./mha/

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
ENTRYPOINT ["python", "-m", "mha.server", "-b", "0.0.0.0"]
