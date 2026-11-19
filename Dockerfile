# n8n + render 2D gratuito (sem Chromium, sem GPU, sem API paga)
FROM node:22-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-numpy python3-pil ffmpeg fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# edge-tts: vozes neurais da Microsoft, de graça e sem chave
RUN pip3 install --break-system-packages edge-tts
RUN npm install -g n8n

COPY render /opt/render

# n8n 2.x desativa o nó Execute Command por padrão e restringe o acesso a arquivos
ENV NODES_EXCLUDE="[]" \
    N8N_RESTRICT_FILE_ACCESS_TO=/data/shorts \
    EXECUTIONS_TIMEOUT=-1

RUN mkdir -p /data/shorts /root/.n8n
EXPOSE 5678
CMD ["n8n", "start"]
