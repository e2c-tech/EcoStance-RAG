FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Build arguments for environment variables
ARG VITE_API_BASE_URL=http://localhost:9000/api/v1
ARG VITE_ENVIRONMENT=production
ARG VITE_BYPASS_AUTH=false

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_ENVIRONMENT=$VITE_ENVIRONMENT
ENV VITE_BYPASS_AUTH=$VITE_BYPASS_AUTH

RUN npm run build

EXPOSE 9002

# Serve the static build using 'serve' on port 9002
CMD ["npx", "serve", "-s", "dist", "-l", "9002"]

