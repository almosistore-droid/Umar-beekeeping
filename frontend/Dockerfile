FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# Slow or unstable networks: npm retries each download, and the whole install is tried up to 3 times
# («npm error Exit handler never called!» is npm giving up on a dropped connection).
ENV NPM_CONFIG_FETCH_RETRIES=6 \
    NPM_CONFIG_FETCH_RETRY_MINTIMEOUT=20000 \
    NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=120000 \
    NPM_CONFIG_FETCH_TIMEOUT=600000 \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_MAXSOCKETS=4
RUN for i in 1 2 3; do npm ci && exit 0; echo "npm ci failed (attempt $i), retrying…"; rm -rf node_modules; sleep 10; done; exit 1
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
