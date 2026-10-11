ARG BASE_IMAGE=ghcr.io/music-assistant/server:2.10.6
FROM ${BASE_IMAGE}
COPY payload/ /tmp/spicy-image-build/
RUN /app/venv/bin/python /tmp/spicy-image-build/install_image.py && rm -rf /tmp/spicy-image-build
LABEL local.spicy-lyrics.version="2.10.6"
