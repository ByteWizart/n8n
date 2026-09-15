FROM n8nio/n8n:1.121.0

USER root

RUN apk add --no-cache \
    ffmpeg \
    fontconfig \
    ttf-dejavu \
    ttf-liberation \
    curl \
    bash \
    && fc-cache -f \
    && mkdir -p /tmp/youtubevideos \
    && chown -R node:node /tmp/youtubevideos \
    && chmod -R 777 /tmp/youtubevideos

USER node
