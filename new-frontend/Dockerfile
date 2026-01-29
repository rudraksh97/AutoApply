# Stage 1: Build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
WORKDIR /usr/share/nginx/html
# Remove default nginx static assets
RUN rm -rf ./*
# Copy static assets from builder stage
COPY --from=builder /app/dist .
# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy env script
COPY env.sh /docker-entrypoint.d/env.sh
RUN chmod +x /docker-entrypoint.d/env.sh

# Start Nginx (the default entrypoint of the nginx image runs the scripts in /docker-entrypoint.d/)
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
