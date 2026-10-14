# Dev only: a Cloudflare quick tunnel that restarts itself and updates the bot's menu button.
FROM cloudflare/cloudflared:latest AS cloudflared

FROM python:3.12-slim
COPY --from=cloudflared /usr/local/bin/cloudflared /usr/local/bin/cloudflared
COPY tunnel.py /tunnel.py
ENV PYTHONUNBUFFERED=1
RUN useradd -r -u 10002 tunnel
USER tunnel
CMD ["python", "/tunnel.py"]
