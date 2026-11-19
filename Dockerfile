# Stage 1: Build the React client
FROM node:22-alpine AS client-build

WORKDIR /app/client

COPY client/package*.json ./
RUN npm ci --legacy-peer-deps

COPY client/ ./

ARG VITE_AUTH0_DOMAIN
ARG VITE_AUTH0_CLIENT_ID
ARG VITE_AUTH0_REDIRECT_URI
ARG VITE_AUTH0_AUDIENCE
ARG VITE_BASE_URL
ARG VITE_GOOGLE_MAPS_API_KEY

ENV VITE_AUTH0_DOMAIN=$VITE_AUTH0_DOMAIN
ENV VITE_AUTH0_CLIENT_ID=$VITE_AUTH0_CLIENT_ID
ENV VITE_AUTH0_REDIRECT_URI=$VITE_AUTH0_REDIRECT_URI
ENV VITE_AUTH0_AUDIENCE=$VITE_AUTH0_AUDIENCE
ENV VITE_BASE_URL=$VITE_BASE_URL
ENV VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY

RUN npm run build

# Stage 2: Python server + static client
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

COPY server/ .

# Copy built client into server's static directory
COPY --from=client-build /app/client/dist ./static

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
