# Neuroion Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Ollama running (either on host or in container)
- Raspberry Pi 5 (for production) or Mac (for development)

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd Neuroion
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Security
SECRET_KEY=your-strong-random-secret-key-here

# Telegram (optional)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Ollama (if not on localhost)
OLLAMA_URL=http://host.docker.internal:11434
```

### 3. Start Services

```bash
cd infra
docker-compose up -d
```

### 4. Verify Services

- Homebase API: http://localhost:8000
- Setup UI: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Raspberry Pi 5 Deployment

### Initial Setup

1. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

2. **Install Docker Compose**:
   ```bash
   sudo apt-get update
   sudo apt-get install docker-compose-plugin
   ```

3. **Clone and Configure**:
   ```bash
   git clone <repository-url>
   cd Neuroion
   # Edit .env file with your configuration
   ```

4. **Start Services**:
   ```bash
   cd infra
   docker-compose up -d
   ```

### Kiosk Mode Setup

1. **Install Chromium**:
   ```bash
   sudo apt-get install chromium-browser
   ```

2. **Configure Auto-start**:
   ```bash
   cd infra/kiosk
   chmod +x start-kiosk.sh
   ```

3. **Add to Autostart** (Raspberry Pi OS):
   Edit `/etc/xdg/lxsession/LXDE-pi/autostart`:
   ```
   @/home/pi/Neuroion/infra/kiosk/start-kiosk.sh
   ```

### Network Configuration

For clients to connect, ensure:

1. **Homebase is accessible on local network**:
   - Find Raspberry Pi IP: `hostname -I`
   - Update client configurations to use this IP

2. **Firewall Rules** (if enabled):
   ```bash
   sudo ufw allow 8000/tcp  # Homebase API
   sudo ufw allow 3000/tcp  # Setup UI
   ```

## Mac Development Setup

### Local Development

1. **Install Dependencies**:
   ```bash
   # Python
   pip install -r neuroion/core/requirements.txt
   
   # Node.js (for setup UI)
   cd setup-ui
   npm install
   ```

2. **Start Ollama**:
   ```bash
   ollama serve
   ```

3. **Start Homebase**:
   ```bash
   cd neuroion/core
   uvicorn neuroion.core.main:app --reload
   ```

4. **Start Setup UI** (new terminal):
   ```bash
   cd setup-ui
   npm run dev
   ```

5. **Start Telegram Bot** (optional, new terminal):
   ```bash
   export TELEGRAM_BOT_TOKEN=your_token
   export HOMEBASE_URL=http://localhost:8000
   python -m telegram.bot
   ```

## Docker Deployment

### Build Images

```bash
cd infra
docker-compose build
```

### Start Services

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f homebase
docker-compose logs -f setup-ui
docker-compose logs -f telegram-bot
```

### Stop Services

```bash
docker-compose down
```

### Update Services

```bash
git pull
cd infra
docker-compose build
docker-compose up -d
```

## Database Management

### Backup

```bash
# If using Docker
docker exec neuroion-homebase cp /data/neuroion.db /data/neuroion.db.backup

# Or directly
cp ~/.neuroion/neuroion.db ~/.neuroion/neuroion.db.backup
```

### Restore

```bash
# Stop services first
docker-compose down

# Restore database
cp neuroion.db.backup ~/.neuroion/neuroion.db

# Start services
docker-compose up -d
```

## Troubleshooting

### Homebase Not Starting

1. Check logs: `docker-compose logs homebase`
2. Verify Ollama is running: `curl http://localhost:11434/api/tags`
3. Check database permissions
4. Verify environment variables

### Setup UI Not Loading

1. Check if Homebase is running: `curl http://localhost:8000/health`
2. Check browser console for errors
3. Verify API URL in setup UI config

### Telegram Bot Not Responding

1. Verify bot token is correct
2. Check Homebase URL is accessible
3. Check logs: `docker-compose logs telegram-bot`

### Database Issues

1. Check database file permissions
2. Verify database path in configuration
3. Check disk space: `df -h`

## Production Checklist

- [ ] Set strong `SECRET_KEY` in environment
- [ ] Configure proper CORS origins
- [ ] Set up database backups
- [ ] Configure firewall rules
- [ ] Set up monitoring/logging
- [ ] Test all client connections
- [ ] Verify Ollama model is downloaded
- [ ] Test pairing flow
- [ ] Verify audit logging works
- [ ] Set up auto-start services

## Monitoring

### Health Checks

```bash
# Homebase health
curl http://localhost:8000/health

# System status (requires auth)
curl -H "Authorization: Bearer <token>" http://localhost:8000/admin/status
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f homebase
```

## Updates

To update Neuroion:

1. Pull latest code: `git pull`
2. Rebuild containers: `docker-compose build`
3. Restart services: `docker-compose up -d`
4. Database migrations run automatically on startup

## Support

For issues and questions, see the main README or open an issue in the repository.
