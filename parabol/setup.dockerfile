# syntax=docker/dockerfile:1

FROM node:22-trixie-slim AS builder
WORKDIR /app

ENV NODE_ENV=production

ARG PUBLIC_URL
ARG CDN_BASE_URL
ENV PUBLIC_URL=${PUBLIC_URL}
ENV CDN_BASE_URL=${CDN_BASE_URL}

COPY pnpm-lock.yaml package.json pnpm-workspace.yaml ./

RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    corepack enable pnpm && \
    pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# Final runtime
FROM node:22-trixie-slim AS runtime
WORKDIR /home/node/parabol

COPY --from=builder /app/build ./build
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules

USER node
EXPOSE 3000
CMD ["node", "dist/web.js"]
