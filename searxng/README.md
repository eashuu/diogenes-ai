# SearXNG Configuration

This directory contains the SearXNG search engine configuration and Docker setup for Diogenes.

## Files

- **`settings.yml`** - SearXNG configuration (custom secret key, bind address, formats)
- **`Dockerfile`** - Docker image definition that includes settings.yml
- **`.dockerignore`** - Docker build context optimization

## Building SearXNG

### Using docker-compose (Recommended)

```bash
# Build and start SearXNG
docker-compose up -d searxng

# Rebuild after changes to settings.yml
docker-compose up -d --build searxng
```

### Using docker directly

```bash
# Build the image
cd searxng
docker build -t diogenes-searxng:latest .

# Run the container
docker run -d \
  --name diogenes-searxng \
  -p 8080:8080 \
  --restart unless-stopped \
  diogenes-searxng:latest
```

## Verifying SearXNG

```bash
# Check if running
curl http://localhost:8080/

# Check container logs
docker logs diogenes-searxng

# Check container status
docker ps | grep searxng
```

## Configuration

The `settings.yml` file contains:

- **`use_default_settings: true`** - Inherits SearXNG defaults
- **`secret_key`** - Custom secret for session security (already configured)
- **`bind_address: "0.0.0.0:8080"`** - Binds to all interfaces inside container
- **`formats`** - Supports HTML and JSON responses

### Modifying Settings

1. Edit `settings.yml` with your changes
2. Rebuild the Docker image:
   ```bash
   docker-compose up -d --build searxng
   ```

### Security Note

The `secret_key` in `settings.yml` should be kept secure. It's used for:
- Session encryption
- Form token generation
- Cookie signing

**Do not commit production secret keys to public repositories!**

## Integration with Diogenes

Diogenes backend connects to SearXNG at `http://localhost:8080` for search queries.

Configuration in `.env`:
```bash
DIOGENES_SEARCH_BASE_URL=http://localhost:8080
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs diogenes-searxng

# Check if port is already in use
netstat -ano | findstr :8080  # Windows
lsof -i :8080                 # Linux/Mac
```

### Permission errors

The Dockerfile sets proper ownership of `/etc/searxng` directory.

### Connection refused

Make sure:
1. Container is running: `docker ps`
2. Port 8080 is exposed: `docker port diogenes-searxng`
3. No firewall blocking: Test with `curl http://localhost:8080/`

## Advanced Configuration

For more advanced SearXNG configuration options, see:
- [SearXNG Documentation](https://docs.searxng.org/)
- [Settings Reference](https://docs.searxng.org/admin/settings/index.html)

## Updating SearXNG

To update to a newer version of SearXNG:

```bash
# Pull latest base image
docker pull searxng/searxng:latest

# Rebuild our custom image
docker-compose up -d --build searxng
```

---

**Note**: SearXNG is a required dependency for Diogenes. The backend will not function without it running.
