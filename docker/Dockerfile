# Multi-stage build serving the Astro static site with Nginx.
# Used for the beta preview deploy; production goes out via GitHub Pages
# (.github/workflows/deploy.yml).

# Stage 1: Build
FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Absolute URLs in the built output (llms.txt, /for-agents) derive from
# Astro's `site`, so the beta must build with its own origin rather than
# inheriting the production one from astro.config.mjs.
ARG SITE_URL=http://localhost:8080
RUN npm run build -- --site "$SITE_URL"

# Stage 2: Serve
FROM nginx:alpine AS server

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
