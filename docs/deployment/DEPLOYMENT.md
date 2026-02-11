# Installation and Deployment Guide

This guide provides detailed instructions for installing and deploying Diogenes in various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 10GB free space minimum
- **Network**: Reliable internet connection for web search

### Software Requirements

- **Python**: 3.10 or higher
- **Node.js**: 18 or higher
- **Git**: Latest version
- **Docker**: 20.10+ (optional, for containerized deployment)
- **Docker Compose**: 1.29+ (optional)

### External Services

- **Ollama**: For local LLM inference (recommended) or cloud LLM API
- **SearXNG**: For web search (included in Docker setup)
- **Browser**: Chrome, Firefox, Safari, or Edge (for frontend)

---

## Local Development

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/diogenes.git
cd diogenes
```

### Step 2: Setup Backend

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows (PowerShell):
venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# (Optional) Install development dependencies
pip install -r requirements-dev.txt
```

### Step 3: Configure Backend

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Minimal required changes:
# DIOGENES_SEARCH_BASE_URL=http://localhost:8080  (if running SearXNG)
# DIOGENES_LLM_BASE_URL=http://localhost:11434    (if running Ollama)
```

### Step 4: Setup Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env.local if needed
cp .env.example .env.local

# Return to project root
cd ..
```

### Step 5: Start Services

#### Option A: Automated Startup (Windows)

```powershell
.\start-diogenes.ps1
```

#### Option B: Manual Startup

**Terminal 1 - SearXNG (Search Engine)**
```bash
docker run -d -p 8080:8080 searxng/searxng
```

**Terminal 2 - Ollama (LLM)**
```bash
# Install from https://ollama.ai first
ollama serve
```

**Terminal 3 - Backend API**
```bash
python run_api.py
```

**Terminal 4 - Frontend**
```bash
cd frontend
npm run dev
```

### Step 6: Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **SearXNG**: http://localhost:8080

---

## Docker Deployment

### Prerequisites

- Docker Desktop or Docker Engine installed
- Docker Compose installed

### Quick Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Remove volumes (caution: deletes data)
docker-compose down -v
```

### Services Started

- **diogenes-backend**: FastAPI backend on port 8000
- **diogenes-frontend**: React frontend on port 5173
- **searxng**: Search engine on port 8080
- **ollama**: LLM service on port 11434

### Accessing Services

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- SearXNG Admin: http://localhost:8080/admin

### Custom Configuration

Edit `docker-compose.yml` to customize:
- Environment variables
- Port mappings
- Volume mounts
- Resource limits

---

## Production Deployment

### Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- HTTPS certificate (Let's Encrypt recommended)
- Reverse proxy (Nginx or Apache)
- Process manager (systemd or supervisor)
- Monitoring tools (optional)

### Backend Deployment

#### 1. Setup Server

```bash
# SSH into server
ssh user@your-server.com

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3.10 python3.10-venv python3-pip git -y

# Clone repository
git clone https://github.com/yourusername/diogenes.git
cd diogenes

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server
```

#### 2. Configure Production Settings

```bash
# Edit .env for production
nano .env

# Set:
DIOGENES_ENV=production
DIOGENES_API_DEBUG=false
DIOGENES_LOG_LEVEL=WARNING
DIOGENES_API_CORS_ORIGINS=https://yourdomain.com
```

#### 3. Setup Systemd Service

Create `/etc/systemd/system/diogenes-backend.service`:

```ini
[Unit]
Description=Diogenes Backend API
After=network.target

[Service]
Type=notify
User=diogenes
WorkingDirectory=/home/diogenes/diogenes
Environment="PATH=/home/diogenes/diogenes/venv/bin"
ExecStart=/home/diogenes/diogenes/venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    src.api.app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable diogenes-backend
sudo systemctl start diogenes-backend
```

### Frontend Deployment

```bash
cd frontend

# Build for production
npm run build

# Output in dist/ directory

# Upload to CDN or web server
# Example with rsync:
rsync -avz dist/ user@your-server.com:/var/www/diogenes/
```

### Nginx Configuration

Create `/etc/nginx/sites-available/diogenes`:

```nginx
upstream diogenes_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        root /var/www/diogenes;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://diogenes_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_cache off;
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/diogenes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### External Services

#### Deploy SearXNG

```bash
# Using Docker
docker pull searxng/searxng
docker run -d \
    -p 8080:8080 \
    -v /etc/searxng:/etc/searxng \
    --name searxng \
    searxng/searxng

# Or use existing SearXNG instance
# Update DIOGENES_SEARCH_BASE_URL in .env
```

#### Deploy Ollama

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3.1:8b
ollama pull qwen2.5:3b

# Expose Ollama API (if remote)
# Run with: OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

### Monitoring

#### Setup Logs

```bash
# Systemd logs
sudo journalctl -u diogenes-backend -f

# Application logs
tail -f /var/log/diogenes/app.log
```

#### Health Check

```bash
# Manual check
curl https://yourdomain.com/api/v1/health/

# Automated monitoring (example with uptimerobot)
# Set health check URL: https://yourdomain.com/api/v1/health/
```

---

## Troubleshooting

### Common Issues

#### Backend Won't Start

**Issue**: `Address already in use`
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

**Issue**: `LLM connection refused`
```bash
# Ensure Ollama is running
ollama serve

# Or update DIOGENES_LLM_BASE_URL in .env
```

#### Frontend Can't Connect to Backend

**Issue**: CORS error in browser console
```
Access-Control-Allow-Origin: missing header
```

**Solution**:
1. Ensure backend is running
2. Check DIOGENES_API_CORS_ORIGINS in backend .env
3. Clear browser cache (Ctrl+Shift+Delete)

#### Search Not Working

**Issue**: SearXNG connection timeout
```bash
# Check if SearXNG is running
curl http://localhost:8080

# If using Docker:
docker ps | grep searxng

# Restart if needed
docker restart searxng
```

### Getting Help

1. Check the [documentation](docs/)
2. Search [existing issues](https://github.com/yourusername/diogenes/issues)
3. Create a [new issue](https://github.com/yourusername/diogenes/issues/new) with:
   - Error messages
   - Configuration (sanitized)
   - Steps to reproduce
   - System information

---

## Performance Tuning

### Backend Optimization

```yaml
# config/production.yaml
crawl:
  max_concurrent: 10  # Increase for faster crawling
  timeout: 60.0       # Adjust based on network

agent:
  max_sources: 15     # More sources = slower but better
  coverage_threshold: 0.8  # Higher = better quality

processing:
  max_total_context: 64000  # More context for better synthesis
```

### Frontend Optimization

```bash
# Build with optimizations
npm run build

# Enable compression in Nginx
gzip on;
gzip_types text/plain text/css application/javascript;
gzip_min_length 1000;
```

---

## Security

### HTTPS/SSL

- Always use HTTPS in production
- Use Let's Encrypt for free certificates
- Renew certificates automatically

### Environment Variables

- Never commit `.env` files
- Use `.env.example` for templates
- Rotate secrets regularly
- Use strong passwords for databases

### API Security

- Consider enabling API key authentication
- Implement rate limiting
- Monitor for suspicious activity
- Keep dependencies updated

---

## Backup and Recovery

### Database Backup

```bash
# SQLite backup
cp data/cache.db backup/cache.db.backup
cp data/sessions.db backup/sessions.db.backup

# Automated backup (cron job)
0 2 * * * /home/diogenes/backup.sh
```

### Recovery

```bash
cp backup/cache.db.backup data/cache.db
systemctl restart diogenes-backend
```

---

For more help, see [docs/](docs/) or open an [issue](https://github.com/yourusername/diogenes/issues).
