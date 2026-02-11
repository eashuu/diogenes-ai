# Dockerfile for SearXNG with custom settings
FROM searxng/searxng:latest

# Copy custom settings
COPY settings.yml /etc/searxng/settings.yml

# Set proper permissions
USER root
RUN chown -R searxng:searxng /etc/searxng
USER searxng

# Expose port 8080
EXPOSE 8080

# Set environment variables
ENV BASE_URL=http://localhost:8080/
ENV INSTANCE_NAME="Diogenes Search"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Start SearXNG
CMD ["python", "/usr/local/searxng/searx/webapp.py"]
