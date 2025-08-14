FROM ollama/ollama:0.11.3

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV OLLAMA_HOST=0.0.0.0:8080
ENV OLLAMA_DEBUG=false
ENV OLLAMA_KEEP_ALIVE=-1
ENV GIN_MODE=release
ENV OLLAMA_NUM_PARALLEL=1
ENV OLLAMA_MAX_LOADED_MODELS=1
ENV OLLAMA_MODELS=/root/.ollama/models

# Start ollama server in background and pull model
RUN ollama serve & \
    sleep 10 && \
    ollama pull gpt-oss:20b && \
    pkill ollama

# Expose port
EXPOSE 8080

# Start ollama server
ENTRYPOINT ["/bin/ollama"]
CMD ["serve"]