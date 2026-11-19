
FROM node:22-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-numpy \
    python3-pil \
    ffmpeg \
    fonts-dejavu-core \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir edge-tts

# Verifica se Python e Edge TTS foram instalados
RUN /usr/bin/python3 --version && /usr/bin/python3 -m edge_tts --help

RUN npm install -g n8n

COPY render /opt/render

ENV NODES_EXCLUDE="[]" \
    N8N_RESTRICT_FILE_ACCESS_TO=/tmp/shorts \
    EXECUTIONS_TIMEOUT=-1 \
    PATH="/usr/local/bin:/usr/bin:/bin"

RUN mkdir -p /tmp/shorts /root/.n8n

EXPOSE 5678

CMD ["n8n", "start"]
