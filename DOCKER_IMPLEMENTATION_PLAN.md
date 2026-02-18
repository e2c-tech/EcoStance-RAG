# Docker Implementation Plan

## Overview
Dockerize the multi-project workspace containing:
- **ecostance-agent-v1**: Python FastAPI backend (RAG system) - Port 9000
- **ecostance-ui-v1**: React/Vite frontend - Port 9002

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose Stack                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐                                            │
│  │ ecostance-ui │                                            │
│  │   (React)    │                                            │
│  │   :9002      │                                            │
│  └──────┬───────┘                                            │
│         │                                                    │
│  ┌──────▼───────┐                                            │
│  │ ecostance-   │                                            │
│  │  agent-v1    │                                            │
│  │  (FastAPI)   │                                            │
│  │   :9000      │                                            │
│  └──────┬───────┘                                            │
│         │                                                    │
│         │                                                    │
│         └──────────► Cloud PostgreSQL (Aiven/Supabase)      │
│                      Cloud Qdrant Vector DB                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: Preparation (COMPLETED ✓)

### 1.1 Environment Configuration ✓
- [x] Created centralized `.env.example`
- [x] Created centralized `.gitignore`
- [x] Created centralized `.dockerignore`
- [x] Pinned all dependency versions in requirements.txt

### 1.2 Cleanup ✓
- [x] Added .env files to .gitignore
- [x] Identified files to exclude from Docker images

## Phase 2: Create Dockerfiles

### 2.1 Backend Dockerfiles

#### ecostance-agent-v1/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 9000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
```

#### c-crm-be/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 9001

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9001"]
```

### 2.2 Frontend Dockerfiles

#### ecostance-ui-v1/Dockerfile
```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 9002

CMD ["nginx", "-g", "daemon off;"]
```

#### c-crm-fe/Dockerfile
```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 9003

CMD ["nginx", "-g", "daemon off;"]
```

## Phase 3: Create Docker Compose Configuration

### 3.1 docker-compose.yml
```yaml
version: '3.8'

services:
  # PostgreSQL Database (for CRM only)
  db:
    image: postgres:16-alpine
    container_name: crm-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-crm_db}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Ecostance Agent Backend
  ecostance-agent:
    build:
      context: ./ecostance-agent-v1
      dockerfile: Dockerfile
    container_name: ecostance-agent
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - QDRANT_URL=${QDRANT_URL}
      - QDRANT_API_KEY=${QDRANT_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    volumes:
      - ./ecostance-agent-v1/uploads:/app/uploads
      - ./ecostance-agent-v1/data:/app/data
    ports:
      - "9000:9000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # CRM Backend
  crm-backend:
    build:
      context: ./c-crm-be
      dockerfile: Dockerfile
    container_name: crm-backend
    environment:
      - CRM_DATABASE_URL=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@db:5432/${POSTGRES_DB:-crm_db}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI}
      - CRM_SECRET_KEY=${CRM_SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Ecostance UI Frontend
  ecostance-ui:
    build:
      context: ./ecostance-ui-v1
      dockerfile: Dockerfile
      args:
        - VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8000/api/v1}
    container_name: ecostance-ui
    depends_on:
      - ecostance-agent
    ports:
      - "9002:9002"

  # CRM Frontend
  crm-frontend:
    build:
      context: ./c-crm-fe
      dockerfile: Dockerfile
      args:
        - VITE_CRM_API_BASE_URL=${VITE_CRM_API_BASE_URL:-http://localhost:9001/api/v1}
    container_name: crm-frontend
    depends_on:
      - crm-backend
    ports:
      - "9003:9003"

volumes:
  postgres_data:
    driver: local

networks:
  default:
    name: app-network
```

## Phase 4: Nginx Configuration for Frontends

### 4.1 ecostance-ui-v1/nginx.conf
```nginx
server {
    listen 3000;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://ecostance-agent:9000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 4.2 c-crm-fe/nginx.conf
```nginx
server {
    listen 3001;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://crm-backend:9001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Phase 5: Backend Modifications

### 5.1 Remove CORS Middleware
Since nginx will handle proxying, CORS middleware is unnecessary and should be removed:

**ecostance-agent-v1/app/main.py**:
- Remove `from fastapi.middleware.cors import CORSMiddleware`
- Remove `app.add_middleware(CORSMiddleware, ...)` block

**c-crm-be/app/main.py**:
- Remove `from fastapi.middleware.cors import CORSMiddleware`
- Remove `origins` list
- Remove `app.add_middleware(CORSMiddleware, ...)` block

### 5.2 Add Health Endpoints to Backends
Both backends need a `/health` endpoint for Docker health checks:

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## Phase 6: Database Migrations

### 6.1 Create Migration Script
```bash
#!/bin/bash
# scripts/init-db.sh

# Wait for PostgreSQL to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

# Run migrations
python -m alembic upgrade head
```

## Phase 7: Environment Variables Setup

### 7.1 Create .env from .env.example
```bash
cp .env.example .env
# Edit .env with actual values
```

### 7.2 Required Environment Variables
- DATABASE_URL (ecostance cloud DB)
- QDRANT_URL, QDRANT_API_KEY
- GOOGLE_API_KEY, GROQ_API_KEY
- JWT_SECRET_KEY, ENCRYPTION_KEY
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
- CRM_SECRET_KEY
- POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

## Phase 8: Build and Deploy

### 8.1 Build Images
```bash
docker-compose build
```

### 8.2 Start Services
```bash
docker-compose up -d
```

### 8.3 View Logs
```bash
docker-compose logs -f
```

### 8.4 Stop Services
```bash
docker-compose down
```

### 8.5 Stop and Remove Volumes
```bash
docker-compose down -v
```

## Phase 9: Testing

### 9.1 Test Checklist
- [ ] All containers start successfully
- [ ] Health checks pass for all services
- [ ] Database connections work
- [ ] API endpoints respond correctly
- [ ] Frontend applications load
- [ ] Frontend can communicate with backends
- [ ] File uploads work (ecostance-agent)
- [ ] Gmail OAuth works (CRM)
- [ ] Cloud database connections work (ecostance)

### 9.2 Test Commands
```bash
# Check container status
docker-compose ps

# Test ecostance-agent API
curl http://localhost:9000/health

# Test CRM API
curl http://localhost:9001/health

# Test frontends
curl http://localhost:9002
curl http://localhost:9003
```

## Phase 10: Production Optimization

### 10.1 Multi-stage Builds
- Already implemented for frontends
- Consider for backends if image size is an issue

### 10.2 Security Hardening
- [ ] Use non-root users in containers
- [ ] Scan images for vulnerabilities
- [ ] Use secrets management (Docker secrets)
- [ ] Enable HTTPS with SSL certificates
- [ ] Implement rate limiting

### 10.3 Performance Optimization
- [ ] Enable caching layers
- [ ] Optimize image sizes
- [ ] Configure resource limits
- [ ] Set up container restart policies

### 10.4 Monitoring & Logging
- [ ] Add logging aggregation (ELK stack)
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure alerts
- [ ] Add APM (Application Performance Monitoring)

## Phase 11: CI/CD Integration

### 11.1 GitHub Actions Workflow
```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build images
        run: docker-compose build
      - name: Push to registry
        run: docker-compose push
```

## Phase 12: Documentation

### 12.1 Create README.md
- [ ] Quick start guide
- [ ] Environment setup instructions
- [ ] Troubleshooting guide
- [ ] API documentation links

### 12.2 Create DEPLOYMENT.md
- [ ] Production deployment steps
- [ ] Cloud provider setup (AWS/GCP/Azure)
- [ ] Domain and SSL configuration
- [ ] Backup and restore procedures

## Execution Order

1. **Phase 2**: Create all Dockerfiles
2. **Phase 4**: Create nginx configurations
3. **Phase 5**: Remove CORS middleware and add health check endpoints
4. **Phase 3**: Create docker-compose.yml
5. **Phase 7**: Setup environment variables
6. **Phase 8**: Build and deploy
7. **Phase 9**: Test everything
8. **Phase 10-12**: Optimize and document

## Estimated Timeline

- Phase 2-4: 2-3 hours (Dockerfile creation)
- Phase 5: 30 minutes (Health endpoints)
- Phase 3: 1 hour (Docker Compose)
- Phase 7-8: 30 minutes (Setup and deploy)
- Phase 9: 1-2 hours (Testing)
- Phase 10-12: 2-4 hours (Optimization)

**Total: 7-11 hours**

## Notes

- ecostance-agent-v1 uses cloud-hosted PostgreSQL (no local DB needed)
- c-crm-be needs local PostgreSQL (included in docker-compose)
- Both frontends use multi-stage builds for smaller images
- Health checks ensure services are ready before dependent services start
- Volumes persist data for uploads and database
