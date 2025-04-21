FROM python:3.10-slim

WORKDIR /app

# Install dependencies - with additional options to address the slow numpy installation
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy all files
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8080

# Run the server
CMD ["python", "simplified_mcp_server.py"]