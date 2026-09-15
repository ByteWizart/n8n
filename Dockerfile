FROM n8nio/n8n:1.121.0

USER root

# Instala ffmpeg + ffprobe + fontes + utilitários
# A imagem oficial do n8n é baseada em Alpine Linux, por isso usamos apk
RUN apk add --no-cache \
    ffmpeg \
    fontconfig \
    ttf-dejavu \
    ttf-liberation \
    curl \
    bash \
    && fc-cache -f

# Cria o diretório do pipeline e libera permissões
RUN mkdir -p /tmp/youtubevideos && chmod -R 777 /tmp/youtubevideos

USER node

# Mantém o entrypoint oficial do n8n
ENTRYPOINT ["tini", "--", "/docker-entrypoint.sh"]
CMD ["n8n", "start"]
