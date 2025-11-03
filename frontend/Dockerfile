# Dockerfile cho React Frontend (Vite)
FROM node:20-alpine AS builder

# Thiết lập working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Cài đặt dependencies
RUN npm ci

# Copy toàn bộ source code
COPY . .

# Build production (VITE_API_URL sẽ được inject từ docker-compose)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files từ builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 8080 (nginx default là 80, nhưng docker-compose map sang 8080)
EXPOSE 80

# Nginx đã có CMD mặc định

