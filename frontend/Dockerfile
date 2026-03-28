FROM node:20-alpine AS base
WORKDIR /app

COPY package.json package-lock.json* ./
# Limit Node memory to prevent OOM on low-RAM VPS (npm ci + next build spike)
ENV NODE_OPTIONS="--max-old-space-size=768"
RUN npm ci

COPY . .

ARG INTERNAL_API_URL=http://backend:8000
ENV INTERNAL_API_URL=$INTERNAL_API_URL

RUN ls src/app/ && ls src/app/planos/ && npm run build

# Standalone mode requires static assets to be copied manually
RUN cp -r .next/static .next/standalone/.next/static && \
    (cp -r public .next/standalone/public 2>/dev/null || true)

EXPOSE 3000

CMD ["node", ".next/standalone/server.js"]
