FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm config set registry https://registry.npmjs.org/ && npm install --no-audit --no-fund

COPY . .

# Build arguments for environment variables
ARG VITE_API_BASE_URL=http://ecostance-agent:9000/api/v1
ARG VITE_ENVIRONMENT=production
ARG VITE_BYPASS_AUTH=false
ARG VITE_LOADER_SRC=https://ai-widget-standalone.pages.dev/loader.js
ARG VITE_API_URL=https://ai.securitycentric.net/ecostance-agent

#ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
#ENV VITE_ENVIRONMENT=$VITE_ENVIRONMENT
#ENV VITE_BYPASS_AUTH=$VITE_BYPASS_AUTH

RUN npm cache clean --force
RUN npm ci
RUN npm run build

#EXPOSE 9002

# Serve the static build using 'serve' on port 9002
#CMD ["npx", "serve", "-s", "dist", "-l", "9002"]


#----- State 2
FROM scratch AS export

WORKDIR /output

#RUN npm install -g serve
#RUN mkdir -p /app/dist
COPY --from=builder /app/dist .


#EXPOSE 9002

#CMD ["serve", "-s", "dist", "-l", "9002"]
CMD ["sh", "-c", "echo 'Build Complete' && sleep 1"]
