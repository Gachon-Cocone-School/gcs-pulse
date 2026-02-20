FROM node:20-bookworm-slim AS builder

WORKDIR /app

COPY package.json package-lock.json turbo.json ./
COPY apps/client/package.json apps/client/package.json
COPY apps/server/package.json apps/server/package.json

RUN npm ci

COPY apps/client ./apps/client

ARG NEXT_PUBLIC_API_URL=https://api.1000.school
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NODE_ENV=production

RUN npm run build --workspace @gcs-mono/client

FROM node:20-bookworm-slim AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/package-lock.json ./package-lock.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/client ./apps/client

EXPOSE 3000

CMD ["npm", "run", "start", "--workspace", "@gcs-mono/client", "--", "-H", "0.0.0.0", "-p", "3000"]
