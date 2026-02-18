FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Build arguments for environment variables
ARG VITE_CRM_API_BASE_URL=http://localhost:9001/api/v1
ARG VITE_ENVIRONMENT=production

ENV VITE_CRM_API_BASE_URL=$VITE_CRM_API_BASE_URL
ENV VITE_ENVIRONMENT=$VITE_ENVIRONMENT

RUN npm run build

EXPOSE 9003

# Serve the static build using 'serve' on port 9003
CMD ["npx", "serve", "-s", "dist", "-l", "9003"]

