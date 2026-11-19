# n8n + tudo que o kit precisa (Node 22, Chromium do Playwright, ffmpeg, Python, Whisper)
FROM node:22-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-numpy python3-pil ffmpeg git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g n8n playwright \
    && npx playwright install --with-deps chromium

# Whisper (faster-whisper): o timing.py usa automaticamente quando está instalado.
# Dá tempos por palavra bem mais precisos para português do que o alinhamento por sílabas em inglês.
RUN pip3 install --break-system-packages faster-whisper \
    && python3 -c "from faster_whisper import WhisperModel; WhisperModel('small', compute_type='int8')"

# O kit (pasta viral-short-skill, do zip corrigido) fica em /opt
COPY viral-short-skill /opt/viral-short-skill

# n8n 2.x desativa o nó Execute Command por padrão e restringe o acesso a arquivos
ENV NODES_EXCLUDE="[]" \
    N8N_RESTRICT_FILE_ACCESS_TO=/data/shorts \
    EXECUTIONS_TIMEOUT=-1 \
    N8N_RUNNERS_ENABLED=true

RUN mkdir -p /data/shorts /root/.n8n
EXPOSE 5678
CMD ["n8n", "start"]
