# ---------- Stage 1: Build static assets ----------
FROM node:20-slim AS frontend-builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

# Copy static assets
COPY app/static ./app/static
COPY esbuild.config.js .

# Run your esbuild build using the config file
RUN npm run build

# ---------- Stage 2: Final image ----------
FROM python:3.11-slim

WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    libsqlite3-dev sqlite3 build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/app/static/dist ./app/static/dist

EXPOSE 8000

# Use uvicorn for FastAPI (no reload in production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
