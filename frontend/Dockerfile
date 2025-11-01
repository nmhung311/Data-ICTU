# Dockerfile cho React Frontend (Vite)
FROM node:20-alpine

# Thiết lập working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Cài đặt dependencies
RUN npm ci

# Copy toàn bộ source code
COPY . .

# Expose port 8080
EXPOSE 8080

# Chạy dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

