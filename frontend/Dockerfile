# syntax=docker/dockerfile:1.7

# ---------- Stage 1: build ----------
FROM node:22-alpine AS build

WORKDIR /app

# Browser-facing URLs default to localhost because the browser runs on
# the host, not inside the Docker network. They can be overridden via
# build args in docker-compose.yml.
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_WS_URL=ws://localhost:8000/ws
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_WS_URL=$VITE_WS_URL

# Install dependencies with strict lockfile usage.
COPY package.json package-lock.json ./
RUN npm ci

# Copy sources and build.
COPY tsconfig.json tsconfig.node.json vite.config.ts ./
COPY index.html ./
COPY postcss.config.js tailwind.config.js ./
COPY src ./src

RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:1.29-alpine AS runtime

# Replace default config with our SPA-friendly one.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# Use nginx's own healthcheck endpoint (we serve a tiny 200 for /healthz).
HEALTHCHECK --interval=10s --timeout=3s --retries=5 --start-period=5s \
    CMD wget -qO- http://localhost/healthz >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
