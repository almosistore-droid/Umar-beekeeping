FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# Slow or unstable server networks:
# - a stalled download is dropped after 60 s and retried (a long timeout made one stuck request wait 10 minutes);
# - IPv4 first: servers without a working IPv6 route hang on the registry's IPv6 address;
# - downloaded packages stay in a build cache, so each new attempt only fetches what is still missing.
ENV NPM_CONFIG_FETCH_RETRIES=10 \
    NPM_CONFIG_FETCH_RETRY_MINTIMEOUT=5000 \
    NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=60000 \
    NPM_CONFIG_FETCH_TIMEOUT=60000 \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_MAXSOCKETS=4 \
    NODE_OPTIONS=--dns-result-order=ipv4first
RUN --mount=type=cache,target=/root/.npm \
    for i in 1 2 3 4 5; do \
      npm ci --prefer-offline && exit 0; \
      echo "npm ci failed (attempt $i of 5), retrying with the packages already downloaded…"; \
      rm -rf node_modules; sleep 10; \
    done; exit 1
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
